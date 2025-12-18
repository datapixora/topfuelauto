"""Celery tasks for auction data crawling and ingestion."""

from celery import Task
from datetime import datetime, timedelta
from sqlalchemy import func
import logging
import httpx

from app.core.database import SessionLocal
from app.workers.celery_app import celery_app
from app.models.auction_tracking import AuctionTracking
from app.models.auction_sale import AuctionSale
from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider
from app.services.sold_results.ingest_service import SoldResultsIngestService
from app.services import proxy_service

logger = logging.getLogger(__name__)


@celery_app.task
def enqueue_bidfax_crawl(
    target_url: str,
    pages: int = 1,
    make: str = None,
    model: str = None,
    schedule_enabled: bool = False,
    schedule_interval_minutes: int = 60,
    proxy_id: int = None,
    fetch_mode: str = "http",
):
    """
    Create auction_tracking rows for each page and enqueue them.

    Supports pagination and scheduled crawls.

    Args:
        target_url: Base Bidfax URL (e.g., https://en.bidfax.info/ford/c-max/)
        pages: Number of pages to crawl (1-100)
        make: Optional vehicle make metadata
        model: Optional vehicle model metadata
        schedule_enabled: If True, set next_check_at for recurring crawls
        schedule_interval_minutes: Interval between scheduled runs
        proxy_id: Optional proxy ID from proxy pool
        fetch_mode: Fetch mode ('http' or 'browser')

    Returns:
        Dictionary with created count and configuration
    """
    db = SessionLocal()
    try:
        created_count = 0

        for page_num in range(1, pages + 1):
            # Build paginated URL
            # Bidfax uses ?page=N parameter
            if page_num == 1:
                page_url = target_url
            else:
                separator = "&" if "?" in target_url else "?"
                page_url = f"{target_url}{separator}page={page_num}"

            # Check if tracking already exists
            existing = db.query(AuctionTracking).filter(
                AuctionTracking.target_url == page_url
            ).first()

            if existing:
                # Update existing tracking to pending
                existing.status = "pending"
                existing.next_check_at = datetime.utcnow()
                existing.make = make
                existing.model = model
                existing.proxy_id = proxy_id
                # Preserve or update fetch_mode in stats
                existing.stats = existing.stats or {}
                existing.stats["fetch_mode"] = fetch_mode
                db.add(existing)
                logger.info(f"Updated existing tracking for {page_url}")
            else:
                # Create new tracking
                next_check = datetime.utcnow()
                if schedule_enabled:
                    # For scheduled crawls, delay first check
                    next_check = next_check + timedelta(minutes=schedule_interval_minutes)

                tracking = AuctionTracking(
                    target_url=page_url,
                    target_type="list_page",
                    make=make,
                    model=model,
                    page_num=page_num,
                    status="pending",
                    next_check_at=next_check,
                    attempts=0,
                    stats={"fetch_mode": fetch_mode},
                    proxy_id=proxy_id,
                )
                db.add(tracking)
                created_count += 1
                logger.info(f"Created tracking for page {page_num}: {page_url}")

        db.commit()

        # Enqueue immediate batch run if not scheduled
        if not schedule_enabled:
            run_tracking_batch.delay(limit=pages)

        return {
            "created": created_count,
            "total_pages": pages,
            "schedule_enabled": schedule_enabled
        }
    finally:
        db.close()


@celery_app.task
def run_tracking_batch(limit: int = 10):
    """
    Find pending/failed tracking rows due for check and enqueue them.

    Called by Celery Beat scheduler every N minutes.
    Implements locking to prevent duplicate processing.

    Args:
        limit: Maximum number of trackings to process in this batch

    Returns:
        Dictionary with enqueued count
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Query for due tracking rows
        # Status: pending or failed
        # next_check_at <= now (due for processing)
        due_trackings = (
            db.query(AuctionTracking)
            .filter(
                AuctionTracking.status.in_(["pending", "failed"]),
                AuctionTracking.next_check_at <= now
            )
            .order_by(AuctionTracking.next_check_at.asc())
            .limit(limit)
            .all()
        )

        enqueued = 0
        for tracking in due_trackings:
            # Mark as running to prevent duplicate processing
            tracking.status = "running"
            tracking.last_seen_at = now
            db.add(tracking)
            db.commit()

            # Enqueue task for processing
            fetch_and_parse_tracking.delay(tracking.id)
            enqueued += 1

        logger.info(f"Enqueued {enqueued} tracking tasks from batch of {len(due_trackings)}")
        return {"enqueued": enqueued}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=0)
def fetch_and_parse_tracking(self: Task, tracking_id: int):
    """
    Fetch and parse a single tracking URL.

    Updates tracking status, stats, and implements exponential backoff on failure.

    Args:
        tracking_id: ID of AuctionTracking row to process

    Returns:
        Ingest statistics dictionary on success
    """
    db = SessionLocal()
    try:
        tracking = db.query(AuctionTracking).filter(AuctionTracking.id == tracking_id).first()
        if not tracking:
            logger.error(f"Tracking {tracking_id} not found")
            return {"error": "tracking_not_found"}

        # Mark as running and increment attempts
        tracking.status = "running"
        tracking.attempts += 1
        db.commit()

        # Initialize provider and ingest service
        provider = BidfaxHtmlProvider(rate_limit_per_minute=30)
        ingest_service = SoldResultsIngestService()

        proxy_url = None
        proxy_exit_ip = None
        proxy_error = None

        # Resolve proxy if provided
        if tracking.proxy_id:
            proxy = proxy_service.get_proxy(db, tracking.proxy_id)
            if not proxy:
                tracking.status = "failed"
                tracking.last_error = f"Proxy {tracking.proxy_id} not found"
                tracking.proxy_error = tracking.last_error
                _set_backoff(tracking)
                db.commit()
                return {"error": "proxy_not_found"}

            proxy_url = proxy_service.build_proxy_url(proxy)
            try:
                check = proxy_service.check_proxy(db, proxy)
                proxy_exit_ip = check.get("exit_ip")
                tracking.proxy_exit_ip = proxy_exit_ip
                if not check.get("ok"):
                    proxy_error = check.get("error") or "proxy check failed"
                    tracking.proxy_error = proxy_error
                    tracking.status = "failed"
                    _set_backoff(tracking)
                    db.commit()
                    return {"error": "proxy_check_failed", "detail": proxy_error}
            except Exception as e:
                proxy_error = str(e)
                tracking.proxy_error = proxy_error
                tracking.status = "failed"
                _set_backoff(tracking)
                db.commit()
                logger.error(f"Proxy check failed for tracking {tracking.id}: {e}")
                return {"error": "proxy_check_exception", "detail": proxy_error}

        # Get fetch_mode from tracking.stats (default to 'http')
        fetch_mode = tracking.stats.get("fetch_mode", "http") if tracking.stats else "http"

        try:
            logger.info(
                "Bidfax fetch started",
                extra={
                    "url": tracking.target_url,
                    "fetch_mode": fetch_mode,
                    "proxy_id": tracking.proxy_id,
                },
            )
            # Fetch HTML using specified mode
            logger.info(f"Fetching {tracking.target_url} (proxy_id={tracking.proxy_id}, fetch_mode={fetch_mode})")
            fetch_result = provider.fetch_list_page(
                url=tracking.target_url,
                proxy_url=proxy_url,
                fetch_mode=fetch_mode,
            )

            # Update diagnostics from fetch result
            tracking.last_http_status = fetch_result.status_code
            if fetch_result.proxy_exit_ip:
                proxy_exit_ip = fetch_result.proxy_exit_ip

            # Check if fetch failed
            if fetch_result.error or not fetch_result.html:
                raise Exception(fetch_result.error or "Fetch returned empty HTML")

            # Parse results
            results = provider.parse_list_page(fetch_result.html, tracking.target_url)
            logger.info(f"Parsed {len(results)} results from {tracking.target_url}")

            # Ingest to database
            ingest_stats = ingest_service.ingest_sold_results(db, results)

            # Update tracking with success
            tracking.status = "done"
            tracking.stats = {
                "items_found": len(results),
                "items_saved": ingest_stats["inserted"] + ingest_stats["updated"],
                "new_records": ingest_stats["inserted"],
                "updated_records": ingest_stats["updated"],
                "skipped": ingest_stats["skipped"],
                "fetch_mode": fetch_mode,  # Preserve fetch_mode
            }
            tracking.last_error = None
            tracking.proxy_error = None
            if proxy_exit_ip:
                tracking.proxy_exit_ip = proxy_exit_ip
            tracking.next_check_at = None  # Clear scheduled time (or set to next if recurring)
            tracking.last_seen_at = datetime.utcnow()

            db.commit()

            logger.info(f"Successfully processed tracking {tracking_id}: {ingest_stats}")
            return ingest_stats

        except httpx.ProxyError as e:
            proxy_error = str(e)
            tracking.proxy_error = proxy_error
            tracking.last_error = f"Proxy error: {proxy_error}"
            tracking.status = "failed"
            tracking.last_http_status = None
            _set_backoff(tracking)
            db.commit()

            logger.error(f"Proxy error for tracking {tracking_id}: {e}")
            return {
                "error": "proxy_error",
                "message": proxy_error,
            }

        except httpx.HTTPStatusError as e:
            # HTTP error (403, 429, 500, etc.)
            tracking.last_http_status = e.response.status_code
            extra_hint = ""
            if e.response.status_code == 403 and not tracking.proxy_id:
                extra_hint = " (blocked; assign a proxy)"
            tracking.last_error = f"HTTP {e.response.status_code}: {str(e)[:200]}{extra_hint}"

            # Determine if blocked or temporary error
            if e.response.status_code in [403, 429]:
                tracking.status = "failed"
                logger.warning(f"Tracking {tracking_id} blocked: {e.response.status_code}")
            else:
                tracking.status = "failed"
                logger.error(f"Tracking {tracking_id} HTTP error: {e.response.status_code}")

            # Set exponential backoff
            _set_backoff(tracking)
            db.commit()

            return {
                "error": "http_error",
                "status_code": e.response.status_code
            }

        except Exception as e:
            # Other errors (parsing, network, database, etc.)
            tracking.status = "failed"
            tracking.last_error = f"{type(e).__name__}: {str(e)[:200]}"
            if proxy_url:
                tracking.proxy_error = tracking.last_error

            # Set exponential backoff
            _set_backoff(tracking)
            db.commit()

            logger.error(f"Tracking {tracking_id} failed: {e}", exc_info=True)

            return {
                "error": "processing_error",
                "message": str(e)[:200]
            }

    finally:
        db.close()


def _set_backoff(tracking: AuctionTracking):
    """
    Set exponential backoff for next_check_at based on attempts.

    Backoff formula: 2^attempts minutes, capped at 24 hours.

    Args:
        tracking: AuctionTracking instance to update
    """
    # Exponential backoff: 2^1 = 2min, 2^2 = 4min, 2^3 = 8min, ..., max 1440min (24h)
    backoff_minutes = min(2 ** tracking.attempts, 1440)
    tracking.next_check_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
    logger.info(
        f"Set backoff for tracking {tracking.id}: {backoff_minutes} minutes "
        f"(attempt {tracking.attempts})"
    )
