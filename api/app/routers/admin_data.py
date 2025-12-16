from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import httpx
import logging

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas import data_engine as schemas
from app.services import data_engine_service as service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/data", tags=["admin-data"])


# ============================================================================
# Admin Sources Endpoints
# ============================================================================

@router.get("/sources", response_model=List[schemas.AdminSourceOut])
def list_sources(
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all admin data sources."""
    return service.list_sources(db, skip=skip, limit=limit, enabled_only=enabled_only)


@router.post("/sources", response_model=schemas.AdminSourceOut, status_code=201)
def create_source(
    source: schemas.AdminSourceCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Create a new admin data source."""
    # Check for duplicate key
    existing = service.get_source_by_key(db, source.key)
    if existing:
        raise HTTPException(status_code=400, detail=f"Source with key '{source.key}' already exists")

    return service.create_source(db, source)


@router.get("/sources/{source_id}", response_model=schemas.AdminSourceOut)
def get_source(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get a specific admin data source."""
    db_source = service.get_source(db, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")
    return db_source


@router.patch("/sources/{source_id}", response_model=schemas.AdminSourceOut)
def update_source(
    source_id: int,
    source_update: schemas.AdminSourceUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Update an admin data source."""
    db_source = service.update_source(db, source_id, source_update)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")
    return db_source


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Delete an admin data source (and cascade delete runs/items)."""
    success = service.delete_source(db, source_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found")
    return None


@router.post("/sources/{source_id}/toggle", response_model=schemas.AdminSourceOut)
def toggle_source(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Toggle source enabled/disabled status."""
    db_source = service.toggle_source(db, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")
    return db_source


@router.post("/sources/{source_id}/run")
def trigger_source_run(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Manually trigger a scraping run for this source (enqueues Celery task).
    Returns task_id for tracking.
    """
    db_source = service.get_source(db, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    if not db_source.is_enabled:
        raise HTTPException(status_code=400, detail="Source is disabled")

    # Enqueue Celery task
    from app.workers.data_engine import run_source_scrape
    task = run_source_scrape.delay(source_id)

    return {
        "task_id": task.id,
        "source_id": source_id,
        "message": "Scraping task enqueued"
    }


@router.get("/sources/{source_id}/runs", response_model=List[schemas.AdminRunOut])
def list_source_runs(
    source_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all runs for a specific source."""
    # Verify source exists
    db_source = service.get_source(db, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    return service.list_runs(db, source_id=source_id, skip=skip, limit=limit)


# ============================================================================
# Admin Runs Endpoints
# ============================================================================

@router.get("/runs/{run_id}", response_model=schemas.AdminRunOut)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get a specific admin run."""
    db_run = service.get_run(db, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
    return db_run


@router.get("/runs/{run_id}/items", response_model=List[schemas.StagedListingOut])
def list_run_items(
    run_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all staged items for a specific run."""
    # Verify run exists
    db_run = service.get_run(db, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")

    return service.list_staged_listings(db, run_id=run_id, skip=skip, limit=limit)


# ============================================================================
# Staged Listings Endpoints
# ============================================================================

@router.get("/staged/{listing_id}", response_model=schemas.StagedListingOut)
def get_staged_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get a specific staged listing with attributes."""
    db_listing = service.get_staged_listing(db, listing_id)
    if not db_listing:
        raise HTTPException(status_code=404, detail="Staged listing not found")
    return db_listing


@router.get("/staged/{listing_id}/attributes", response_model=List[schemas.StagedListingAttributeOut])
def get_staged_listing_attributes(
    listing_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get attributes for a specific staged listing."""
    db_listing = service.get_staged_listing(db, listing_id)
    if not db_listing:
        raise HTTPException(status_code=404, detail="Staged listing not found")
    return db_listing.attributes


@router.get("/staged", response_model=List[schemas.StagedListingOut])
def list_all_staged_listings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all staged listings."""
    return service.list_staged_listings(db, skip=skip, limit=limit)


# ============================================================================
# Proxy Testing Endpoint
# ============================================================================

class ProxyTestRequest(BaseModel):
    proxy_url: str
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    test_url: str = "https://httpbin.org/ip"


class ProxyTestResponse(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[int] = None
    response_data: Optional[dict] = None


@router.post("/test-proxy", response_model=ProxyTestResponse)
async def test_proxy(
    request: ProxyTestRequest,
    admin: User = Depends(get_current_admin),
):
    """
    Test proxy connectivity by making a simple HTTP request.
    Returns success status, latency, and response data.
    """
    import time

    try:
        # Build proxy URL with authentication
        proxy_url = request.proxy_url
        if request.proxy_username and request.proxy_password:
            # Parse proxy URL to inject credentials
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(proxy_url)
            proxy_url = urlunparse((
                parsed.scheme,
                f"{request.proxy_username}:{request.proxy_password}@{parsed.netloc}",
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))

        # Configure httpx client with proxy
        proxies = {
            "http://": proxy_url,
            "https://": proxy_url,
        }

        start = time.time()
        async with httpx.AsyncClient(proxies=proxies, timeout=10.0) as client:
            response = await client.get(request.test_url)
            latency = int((time.time() - start) * 1000)

            if response.status_code == 200:
                try:
                    data = response.json()
                except:
                    data = {"text": response.text[:200]}

                return ProxyTestResponse(
                    success=True,
                    message=f"Proxy connection successful (HTTP {response.status_code})",
                    latency_ms=latency,
                    response_data=data
                )
            else:
                return ProxyTestResponse(
                    success=False,
                    message=f"Proxy returned HTTP {response.status_code}",
                    latency_ms=latency,
                    response_data=None
                )

    except httpx.ProxyError as e:
        logger.error(f"Proxy error: {e}")
        return ProxyTestResponse(
            success=False,
            message=f"Proxy connection failed: {str(e)}",
            latency_ms=None,
            response_data=None
        )
    except httpx.TimeoutException:
        return ProxyTestResponse(
            success=False,
            message="Proxy connection timed out (10s)",
            latency_ms=None,
            response_data=None
        )
    except Exception as e:
        logger.error(f"Unexpected proxy test error: {e}")
        return ProxyTestResponse(
            success=False,
            message=f"Test failed: {str(e)}",
            latency_ms=None,
            response_data=None
        )
