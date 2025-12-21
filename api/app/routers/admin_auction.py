"""Admin API endpoints for auction sold results (Bidfax crawling)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime
import httpx

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
            strategy_id=job.strategy_id,
            watch_mode=job.watch_mode,
            use_2captcha=job.use_2captcha,
            batch_size=job.batch_size,
            rpm=job.rpm,
            concurrency=job.concurrency,
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


@router.get("/strategies", response_model=List[schemas.StrategyResponse])
def list_strategies(
    admin: User = Depends(get_current_admin),
):
    """
    List available scraping strategies.

    Returns metadata for all registered strategies including:
    - Strategy ID and label
    - Supported fetch modes (http/browser)
    - Watch mode availability (local dev only)
    - 2Captcha support
    - Usage notes

    Example response:
    ```json
    [
      {
        "id": "bidfax_browser",
        "label": "Bidfax Browser (Robust)",
        "description": "Playwright browser with cookie and 2Captcha support",
        "supports_fetch_modes": ["browser"],
        "supports_watch_mode": true,
        "default_fetch_mode": "browser",
        "supports_2captcha": true,
        "notes": "Slower but bypasses Cloudflare. Supports visual watch mode in local dev."
      }
    ]
    ```
    """
    from app.services.sold_results.strategy_registry import list_strategies as get_all_strategies

    strategies = get_all_strategies()

    # Convert dataclass to dict for Pydantic
    return [
        schemas.StrategyResponse(
            id=s.id,
            label=s.label,
            description=s.description,
            supports_fetch_modes=s.supports_fetch_modes,
            supports_watch_mode=s.supports_watch_mode,
            default_fetch_mode=s.default_fetch_mode,
            supports_2captcha=s.supports_2captcha,
            notes=s.notes,
        )
        for s in strategies
    ]


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
    import time
    from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider

    start_time = time.time()
    proxy_used = False
    proxy_name = None
    proxy_exit_ip = None
    proxy_error = None
    http_status = 0
    http_error = None

    try:
        # Resolve proxy if specified
        chosen_proxy = None
        proxy_url = None

        def build_proxy(proxy):
            return proxy_service.build_proxy_url(proxy)

        if request.proxy_id:
            proxy = proxy_service.get_proxy(db, request.proxy_id)
            if not proxy:
                raise HTTPException(status_code=404, detail="Proxy not found")
            chosen_proxy = proxy

        # If not provided or if chosen is unhealthy, try first healthy enabled proxy
        if not chosen_proxy:
            now = datetime.utcnow()
            healthy = [
                p for p in proxy_service.list_enabled_proxies(db)
                if not p.unhealthy_until or p.unhealthy_until <= now
            ]
            if healthy:
                chosen_proxy = healthy[0]

        if chosen_proxy:
            proxy_url = build_proxy(chosen_proxy)
            proxy_name = chosen_proxy.name
            proxy_used = True

            # Check proxy health
            try:
                check = proxy_service.check_proxy(db, chosen_proxy)
                proxy_exit_ip = check.get("exit_ip")
                if not check.get("ok"):
                    proxy_error = check.get("error")
                    error_code = check.get("error_code")
                    raise HTTPException(status_code=502, detail=f"Proxy check failed: {proxy_error}", headers={"X-Proxy-Error-Code": error_code or ""})
            except HTTPException:
                raise
            except Exception as e:
                proxy_error = str(e)
                logger.warning(f"Proxy check failed for test-parse: {e}")

        logger.info(
            "BIDFAX TEST-PARSE RECEIVED",
            extra={
                "url": request.url,
                "fetch_mode": request.fetch_mode,
                "proxy_id": request.proxy_id,
                "watch_mode": request.watch_mode,
                "use_2captcha": request.use_2captcha,
            },
        )
        # Fetch HTML using specified mode with strategy parameters
        provider = BidfaxHtmlProvider(
            watch_mode=request.watch_mode,
            use_2captcha=request.use_2captcha,
        )
        logger.info(
            "Bidfax fetch started",
            extra={
                "url": request.url,
                "fetch_mode": request.fetch_mode,
                "proxy_id": request.proxy_id,
                "has_cookies": bool(request.cookies),
                "watch_mode": request.watch_mode,
                "use_2captcha": request.use_2captcha,
            },
        )
        fetch_result = provider.fetch_list_page(
            url=request.url,
            proxy_url=proxy_url,
            fetch_mode=request.fetch_mode,
            cookies=request.cookies,
        )

        # Update diagnostics from fetch result
        http_status = fetch_result.status_code
        latency_ms = fetch_result.latency_ms
        if fetch_result.error:
            http_error = fetch_result.error
        if fetch_result.proxy_exit_ip:
            proxy_exit_ip = fetch_result.proxy_exit_ip

        # Check if fetch failed
        if fetch_result.error or not fetch_result.html:
            raise Exception(fetch_result.error or "Fetch returned empty HTML")

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

        logger.info(f"Admin {admin.email} tested parse for {request.url}: {len(results)} found, parse_ok={parse_ok}")

        return schemas.BidfaxTestParseResponse(
            ok=True,
            http=schemas.HttpInfo(
                status=http_status,
                error=None,
                latency_ms=latency_ms,
            ),
            proxy=schemas.ProxyInfo(
                used=proxy_used,
                proxy_id=request.proxy_id,
                proxy_name=proxy_name,
                exit_ip=proxy_exit_ip,
                error=proxy_error,
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
                fetch_mode=request.fetch_mode,
                cloudflare_bypassed=fetch_result.cloudflare_bypassed,
                cookies_used=bool(fetch_result.cookies_used),
            ),
            fetch_mode=request.fetch_mode,
            final_url=fetch_result.final_url,
            html=fetch_result.html,
        )

    except httpx.HTTPStatusError as e:
        http_status = e.response.status_code
        latency_ms = int((time.time() - start_time) * 1000)
        http_error = f"HTTP {http_status}: {str(e)}"

        if http_status == 403 and not request.proxy_id:
            http_error += " (blocked; try using a proxy)"

        logger.error(f"Test parse HTTP error for {request.url}: {e}", exc_info=True)

        return schemas.BidfaxTestParseResponse(
            ok=False,
            http=schemas.HttpInfo(
                status=http_status,
                error=http_error,
                latency_ms=latency_ms,
            ),
            proxy=schemas.ProxyInfo(
                used=proxy_used,
                proxy_id=request.proxy_id,
                proxy_name=proxy_name,
                exit_ip=proxy_exit_ip,
                error=proxy_error,
                error_code=e.headers.get("X-Proxy-Error-Code") if hasattr(e, "headers") and e.headers else None,
                stage="proxy_check" if proxy_error else None,
            ),
            parse=schemas.ParseInfo(
                ok=False,
                missing=[],
            ),
            debug=schemas.DebugInfo(
                url=request.url,
                provider="bidfax_html",
                fetch_mode=request.fetch_mode,
                cloudflare_bypassed=fetch_result.cloudflare_bypassed if 'fetch_result' in locals() else False,
                cookies_used=bool(fetch_result.cookies_used) if 'fetch_result' in locals() else False,
            ),
            fetch_mode=request.fetch_mode,
            final_url=fetch_result.final_url if 'fetch_result' in locals() else request.url,
            html=fetch_result.html if 'fetch_result' in locals() else "",
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Test parse failed for {request.url}: {e}", exc_info=True)
        proxy_error_code = None
        if isinstance(e, HTTPException) and e.headers:
            proxy_error_code = e.headers.get("X-Proxy-Error-Code")

        return schemas.BidfaxTestParseResponse(
            ok=False,
            http=schemas.HttpInfo(
                status=http_status or 0,
                error=error_msg,
                latency_ms=latency_ms,
            ),
            proxy=schemas.ProxyInfo(
                used=proxy_used,
                proxy_id=request.proxy_id,
                proxy_name=proxy_name,
                exit_ip=proxy_exit_ip,
                error=proxy_error or error_msg,
                error_code=proxy_error_code,
                stage="proxy_check" if proxy_error or proxy_error_code else None,
            ),
            parse=schemas.ParseInfo(
                ok=False,
                missing=[],
            ),
            debug=schemas.DebugInfo(
                url=request.url,
                provider="bidfax_html",
                fetch_mode=request.fetch_mode,
                cloudflare_bypassed=fetch_result.cloudflare_bypassed if 'fetch_result' in locals() else False,
                cookies_used=bool(fetch_result.cookies_used) if 'fetch_result' in locals() else False,
            ),
            fetch_mode=request.fetch_mode,
            final_url=fetch_result.final_url if 'fetch_result' in locals() else request.url,
            html=fetch_result.html if 'fetch_result' in locals() else "",
        )


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
