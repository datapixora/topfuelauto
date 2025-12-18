"""Admin API endpoints for auction sold results (Bidfax crawling)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.auction_sale import AuctionSale
from app.models.auction_tracking import AuctionTracking
from app.schemas import auction as schemas
from app.workers import auction as tasks
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
        # Enqueue Celery task
        result = tasks.enqueue_bidfax_crawl.delay(
            target_url=job.target_url,
            pages=job.pages,
            make=job.make,
            model=job.model,
            schedule_enabled=job.schedule_enabled,
            schedule_interval_minutes=job.schedule_interval_minutes,
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


@router.post("/test-parse", response_model=dict)
def test_parse_url(
    url: str = Query(..., description="Bidfax URL to test parse"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Test URL parsing without saving to database.

    Fetches the URL, parses with BidfaxHtmlProvider, and returns first 3 items.
    Useful for validating selectors and debugging parsing issues.

    Example:
        POST /test-parse?url=https://en.bidfax.info/ford/c-max/

    Returns:
        Dictionary with:
        - success: bool
        - total_found: int
        - preview: List of first 3 parsed items
        OR
        - success: false
        - error: str
    """
    try:
        from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider

        provider = BidfaxHtmlProvider()

        # Fetch HTML
        html = provider.fetch_list_page(url)

        # Parse results
        results = provider.parse_list_page(html, url)

        # Return first 3 items for preview
        preview = results[:3]

        logger.info(f"Admin {admin.email} tested parse for {url}: {len(results)} found")

        return {
            "success": True,
            "total_found": len(results),
            "preview": preview,
        }
    except Exception as e:
        logger.error(f"Test parse failed for {url}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}",
        }


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
