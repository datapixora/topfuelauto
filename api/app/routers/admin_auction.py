"""Admin API endpoints for auction sold results (Bidfax crawling)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime
import time
import uuid

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.auction_sale import AuctionSale
from app.models.auction_tracking import AuctionTracking
from app.schemas import auction as schemas
from app.workers import auction as tasks
from app.services import proxy_service
import logging

router = APIRouter(prefix="/api/v1/admin/data-engine/bidfax", tags=["admin", "auction"])
logger = logging.getLogger(__name__)


@router.post("/jobs", response_model=dict, status_code=201)
def create_bidfax_job(
    job: schemas.BidfaxJobCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Create a new Bidfax crawl job.

    Enqueues tracking rows for the specified number of pages.
    Supports one-off crawls and recurring scheduled crawls.

    Example request:
    ```json
    {
      "target_url": "https://en.bidfax.info/ford/c-max/",
      "pages": 5,
      "make": "Ford",
      "model": "C-Max",
      "schedule_enabled": false
    }
    ```

    Returns:
        Job creation confirmation with task_id
    """
    try:
        proxy_id = job.proxy_id
        if proxy_id:
            proxy = proxy_service.get_proxy(db, proxy_id)
            if not proxy:
                raise HTTPException(status_code=404, detail=f"Proxy {proxy_id} not found")

        # Enqueue Celery task
        result = tasks.enqueue_bidfax_crawl.delay(
            target_url=job.target_url,
            pages=job.pages,
            make=job.make,
            model=job.model,
            schedule_enabled=job.schedule_enabled,
            schedule_interval_minutes=job.schedule_interval_minutes,
            proxy_id=proxy_id,
            fetch_mode=job.fetch_mode,
        )

        logger.info(
            f"Admin {admin.email} created Bidfax job: {job.target_url} "
            f"({job.pages} pages, schedule={job.schedule_enabled})"
        )

        return {
            "message": "Job created successfully",
            "task_id": result.id,
            "target_url": job.target_url,
            "pages": job.pages,
            "schedule_enabled": job.schedule_enabled,
        }
    except Exception as e:
        logger.error(f"Failed to create Bidfax job: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to enqueue job. Celery worker may not be running: {str(e)}"
        )


@router.get("/tracking", response_model=dict)
def list_tracking(
    status: Optional[str] = Query(None, description="Filter by status (pending/running/done/failed)"),
    make: Optional[str] = Query(None, description="Filter by make"),
    model: Optional[str] = Query(None, description="Filter by model"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Results offset for pagination"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    List auction tracking rows with filters and status counts.

    Returns:
        Dictionary with:
        - counts: Status counts (pending/running/done/failed)
        - trackings: List of tracking rows
        - total: Total matching rows
        - limit/offset: Pagination info
    """
    # Build query with filters
    query = db.query(AuctionTracking)

    if status:
        query = query.filter(AuctionTracking.status == status)
    if make:
        query = query.filter(AuctionTracking.make.ilike(f"%{make}%"))
    if model:
        query = query.filter(AuctionTracking.model.ilike(f"%{model}%"))

    # Get status counts (aggregate across all trackings, not just filtered)
    status_counts = dict(
        db.query(AuctionTracking.status, func.count(AuctionTracking.id))
        .group_by(AuctionTracking.status)
        .all()
    )

    # Get paginated results
    total = query.count()
    trackings = (
        query
        .order_by(desc(AuctionTracking.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "counts": status_counts,
        "trackings": [schemas.AuctionTrackingResponse.from_orm(t) for t in trackings],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/tracking/{tracking_id}/retry", response_model=schemas.AuctionTrackingResponse)
def retry_tracking(
    tracking_id: int,
    request: schemas.TrackingRetryRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Retry a failed tracking row.

    Sets status to pending, next_check_at to now, and optionally resets attempt counter.
    Immediately enqueues the tracking for processing.

    Args:
        tracking_id: ID of tracking to retry
        request: Retry configuration (reset_attempts flag)

    Returns:
        Updated tracking row
    """
    tracking = db.query(AuctionTracking).filter(AuctionTracking.id == tracking_id).first()
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")

    # Update status to pending
    tracking.status = "pending"
    tracking.next_check_at = datetime.utcnow()

    if request.reset_attempts:
        tracking.attempts = 0
        logger.info(f"Admin {admin.email} reset attempts for tracking {tracking_id}")

    db.commit()
    db.refresh(tracking)

    logger.info(f"Admin {admin.email} retried tracking {tracking_id}")

    # Enqueue immediately for processing
    try:
        tasks.fetch_and_parse_tracking.delay(tracking_id)
    except Exception as e:
        logger.warning(f"Failed to enqueue tracking {tracking_id}: {e}")
        # Don't fail the request - tracking is already updated

    return tracking


@router.get("/auction-sales", response_model=List[schemas.AuctionSaleResponse])
def list_auction_sales(
    vin: Optional[str] = Query(None, description="Filter by VIN (17-char)"),
    auction_source: Optional[str] = Query(None, description="Filter by auction source (copart/iaai)"),
    start_date: Optional[datetime] = Query(None, description="Filter sold_at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter sold_at <= end_date"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    List auction sales with filters and pagination.

    Useful for viewing ingested sold results and price history.

    Returns:
        List of auction sale records
    """
    query = db.query(AuctionSale)

    # Apply filters
    if vin:
        query = query.filter(AuctionSale.vin == vin.upper())
    if auction_source:
        query = query.filter(AuctionSale.auction_source == auction_source)
    if start_date:
        query = query.filter(AuctionSale.sold_at >= start_date)
    if end_date:
        query = query.filter(AuctionSale.sold_at <= end_date)

    # Get paginated results, ordered by sold_at (most recent first)
    sales = (
        query
        .order_by(desc(AuctionSale.sold_at), desc(AuctionSale.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return sales


@router.post("/test-parse", response_model=schemas.BidfaxTestParseResponse)
def test_parse_url(
    request: schemas.BidfaxTestParseRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Test URL parsing without saving to database.

    Fetches the URL, parses with BidfaxHtmlProvider, and returns structured diagnostics.
    Useful for validating selectors and debugging parsing/proxy issues.

    Example:
        POST /test-parse {"url":"https://en.bidfax.info/ford/c-max/","proxy_id":1}

    Returns:
        BidfaxTestParseResponse with http/proxy/parse/debug sections
    """
    from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider

    start_time = time.time()
    request_id = str(uuid.uuid4())
    provider = BidfaxHtmlProvider()
    proxy_used = False
    proxy_name = None
    proxy_exit_ip = None
    proxy_error = None
    proxy_error_code = None
    proxy_stage = None
    proxy_url = None
    chosen_proxy = None
    proxy_latency_ms = None
    proxy_id = request.proxy_id
    if proxy_id in ("", 0):
        proxy_id = None
    fetch_mode = request.fetch_mode

    def fail_response(code: Optional[str], stage: Optional[str], message: str, http_status: int = 0, latency_ms: int = 0):
        error_obj = schemas.ErrorInfo(code=code, stage=stage, message=message)
        return schemas.BidfaxTestParseResponse(
            ok=False,
            http=schemas.HttpInfo(
                status=http_status,
                error=message,
                latency_ms=latency_ms,
            ),
            proxy=schemas.ProxyInfo(
                used=proxy_used,
                proxy_id=chosen_proxy.id if chosen_proxy else proxy_id,
                proxy_name=proxy_name,
                exit_ip=proxy_exit_ip,
                error=message,
                error_code=code,
                stage=stage,
                latency_ms=proxy_latency_ms,
            ),
            parse=schemas.ParseInfo(
                ok=False,
                missing=[],
            ),
            debug=schemas.DebugInfo(
                url=request.url,
                provider="bidfax_html",
                fetch_mode=fetch_mode,
                request_id=request_id,
            ),
            fetch_mode=fetch_mode,
            final_url=request.url,
            html="",
            error=error_obj,
        )

    def _healthy_proxies(exclude_ids: Optional[set[int]] = None):
        now = datetime.utcnow()
        exclude = exclude_ids or set()
        return [
            p for p in proxy_service.list_enabled_proxies(db)
            if p.id not in exclude and (not p.unhealthy_until or p.unhealthy_until <= now)
        ]

    # Validate fetch_mode
    if fetch_mode not in ("http", "browser"):
        return fail_response("INVALID_FETCH_MODE", "validate", f"Invalid fetch_mode: {fetch_mode}")

    try:
        # Build proxy candidate list (max 2 attempts)
        proxy_candidates = []
        if proxy_id:
            proxy = proxy_service.get_proxy(db, proxy_id)
            if not proxy:
                raise HTTPException(status_code=404, detail="Proxy not found")
            proxy_candidates.append(proxy)
            alt = _healthy_proxies({proxy.id})
            if alt:
                proxy_candidates.append(alt[0])
        else:
            primary = _healthy_proxies()
            if primary:
                proxy_candidates.append(primary[0])
                alt = _healthy_proxies({primary[0].id})
                if alt:
                    proxy_candidates.append(alt[0])

        proxy_check_result = None
        for candidate in proxy_candidates[:2]:
            proxy_used = True
            proxy_name = candidate.name
            proxy_url_candidate = proxy_service.build_proxy_url(candidate)
            proxy_check_result = proxy_service.check_proxy(db, candidate)
            proxy_stage = proxy_check_result.get("stage")
            proxy_error_code = proxy_check_result.get("error_code")
            candidate_exit_ip = proxy_check_result.get("exit_ip")
            if candidate_exit_ip:
                proxy_exit_ip = candidate_exit_ip
            if proxy_check_result.get("ok"):
                chosen_proxy = candidate
                proxy_url = proxy_url_candidate
                break
            proxy_error = proxy_check_result.get("error")
            if isinstance(proxy_error, dict):
                proxy_error = proxy_error.get("message") or proxy_error.get("detail")

        if proxy_check_result:
            if proxy_stage == "proxy_check_https":
                proxy_latency_ms = (proxy_check_result.get("https") or {}).get("latency_ms")
            elif proxy_stage == "proxy_check_http":
                proxy_latency_ms = (proxy_check_result.get("http") or {}).get("latency_ms")

        if proxy_candidates and not chosen_proxy:
            latency_ms = int((time.time() - start_time) * 1000)
            code = proxy_error_code or "NO_HEALTHY_PROXY"
            message = proxy_error or "No healthy proxies available"
            last_candidate = proxy_candidates[-1]
            return schemas.BidfaxTestParseResponse(
                ok=False,
                http=schemas.HttpInfo(
                    status=0,
                    error=message,
                    latency_ms=latency_ms,
                ),
                proxy=schemas.ProxyInfo(
                    used=True,
                    proxy_id=last_candidate.id,
                    proxy_name=last_candidate.name,
                    exit_ip=proxy_exit_ip,
                    error=message,
                    error_code=code,
                    stage=proxy_stage or "proxy_check_http",
                    latency_ms=proxy_latency_ms,
                ),
                parse=schemas.ParseInfo(
                    ok=False,
                    missing=[],
                ),
                debug=schemas.DebugInfo(
                    url=request.url,
                    provider="bidfax_html",
                    fetch_mode=fetch_mode,
                    request_id=request_id,
                ),
                fetch_mode=fetch_mode,
                final_url=request.url,
                html="",
                error=schemas.ErrorInfo(code=code, stage=proxy_stage or "proxy_check_http", message=message),
            )

        # Logging context
        logger.info(
            "BIDFAX TEST-PARSE RECEIVED",
            extra={
                "url": request.url,
                "fetch_mode": fetch_mode,
                "proxy_id": chosen_proxy.id if chosen_proxy else proxy_id,
                "request_id": request_id,
            },
        )

        fetch_result = provider.fetch_list_page(
            url=request.url,
            proxy_url=proxy_url,
            proxy_id=chosen_proxy.id if chosen_proxy else proxy_id,
            fetch_mode=fetch_mode,
        )

        # Update diagnostics from fetch result
        http_status = fetch_result.status_code or 0
        latency_ms = fetch_result.latency_ms
        http_error = fetch_result.error
        if fetch_result.proxy_exit_ip:
            proxy_exit_ip = fetch_result.proxy_exit_ip

        # Check if fetch failed
        if fetch_result.error or not fetch_result.html:
            message = http_error or "Fetch returned empty HTML"
            if http_status == 403 and not proxy_used:
                message += " (blocked; try using a proxy)"
            code = "EMPTY_HTML" if not fetch_result.html else proxy_error_code
            return fail_response(code, f"fetch_{fetch_mode}", message, http_status=http_status, latency_ms=latency_ms)

        # Parse results
        results = provider.parse_list_page(fetch_result.html, request.url)

        # Validate first result for completeness
        missing_fields = []
        first_result = results[0] if results else {}
        if first_result:
            if not first_result.get("vin"):
                missing_fields.append("vin")
            if not first_result.get("sold_price"):
                missing_fields.append("sold_price")
            if not first_result.get("lot_id"):
                missing_fields.append("lot_id")

        parse_ok = len(results) > 0 and len(missing_fields) == 0

        logger.info(
            "BIDFAX TEST-PARSE SUCCESS",
            extra={
                "url": request.url,
                "fetch_mode": fetch_mode,
                "proxy_id": chosen_proxy.id if chosen_proxy else proxy_id,
                "request_id": request_id,
                "items_found": len(results),
            },
        )

        return schemas.BidfaxTestParseResponse(
            ok=True,
            http=schemas.HttpInfo(
                status=http_status,
                error=None,
                latency_ms=latency_ms,
            ),
            proxy=schemas.ProxyInfo(
                used=proxy_used,
                proxy_id=chosen_proxy.id if chosen_proxy else proxy_id,
                proxy_name=proxy_name,
                exit_ip=proxy_exit_ip,
                error=proxy_error,
                error_code=proxy_error_code,
                stage=proxy_stage,
                latency_ms=proxy_latency_ms,
            ),
            parse=schemas.ParseInfo(
                ok=parse_ok,
                missing=missing_fields,
                sale_status=first_result.get("sale_status") if first_result else None,
                final_bid=first_result.get("sold_price") if first_result else None,
                vin=first_result.get("vin") if first_result else None,
                lot_id=first_result.get("lot_id") if first_result else None,
                sold_at=first_result.get("sold_at").isoformat() if first_result and first_result.get("sold_at") else None,
            ),
            debug=schemas.DebugInfo(
                url=request.url,
                provider="bidfax_html",
                fetch_mode=fetch_mode,
                request_id=request_id,
            ),
            fetch_mode=fetch_mode,
            final_url=fetch_result.final_url,
            html=fetch_result.html,
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "sold-results test-parse failed",
            extra={"request_id": request_id, "url": request.url, "proxy_id": proxy_id, "fetch_mode": fetch_mode},
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}")


@router.get("/listings/{listing_id}/sold-results", response_model=List[schemas.AuctionSaleResponse])
def get_listing_sold_results(
    listing_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Get auction sales matching a listing's VIN or lot_id.

    Useful for enriching listing detail pages with sold price history
    and for pricing intelligence features (Expected Sold Price, Deal Score).

    Args:
        listing_id: MergedListing ID

    Returns:
        List of matching AuctionSale records (up to 10 most recent)
    """
    from app.models.merged_listing import MergedListing

    # Get listing
    listing = db.query(MergedListing).filter(MergedListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Extract VIN from listing (may be in extra JSONB field)
    vin = listing.extra.get("vin") if listing.extra else None
    lot_id = listing.source_listing_id

    # Query auction_sales
    query = db.query(AuctionSale)

    if vin:
        # Match by VIN (strongest identifier)
        query = query.filter(AuctionSale.vin == vin.upper())
    elif lot_id:
        # Fallback: Match by lot_id
        query = query.filter(AuctionSale.lot_id == lot_id)
    else:
        # No identifiers available
        logger.warning(f"Listing {listing_id} has no VIN or lot_id for auction matching")
        return []

    # Get up to 10 most recent sales
    sales = query.order_by(desc(AuctionSale.sold_at)).limit(10).all()

    logger.info(f"Found {len(sales)} auction sales for listing {listing_id}")

    return sales
