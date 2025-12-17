from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import httpx
import logging

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas import data_engine as schemas
from app.services import data_engine_service as service
from app.services import source_detect_service
from app.services import source_extract_service

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
    sources = service.list_sources(db, skip=skip, limit=limit, enabled_only=enabled_only)

    # Attach proxy pool summary for sources using pool mode
    proxy_pool_summary = None
    for source in sources:
        if source.proxy_mode == "pool":
            if proxy_pool_summary is None:  # Compute once and reuse
                proxy_pool_summary = service.get_proxy_pool_summary(db)
            source.proxy_pool_summary = proxy_pool_summary
        else:
            source.proxy_pool_summary = None

    return sources


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

    # Attach proxy pool summary if using pool mode
    if db_source.proxy_mode == "pool":
        db_source.proxy_pool_summary = service.get_proxy_pool_summary(db)
    else:
        db_source.proxy_pool_summary = None

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

    # Attach proxy pool summary if using pool mode
    if db_source.proxy_mode == "pool":
        db_source.proxy_pool_summary = service.get_proxy_pool_summary(db)
    else:
        db_source.proxy_pool_summary = None

    return db_source


class SourceDetectRequest(BaseModel):
    url: Optional[str] = None
    try_proxy: Optional[bool] = None
    try_playwright: Optional[bool] = None


@router.post("/sources/{source_id}/detect")
def detect_source(
    source_id: int,
    request: SourceDetectRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Auto-detect a source strategy by fetching HTML and applying lightweight fingerprints.

    - Attempts direct httpx first
    - Optionally retries with proxy (if configured) and/or Playwright
    - Stores latest detect report to source.settings_json.detect_report and source.settings_json.detected_strategy
    """
    db_source = service.get_source(db, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    settings_json = db_source.settings_json or {}
    targets = settings_json.get("targets") if isinstance(settings_json.get("targets"), dict) else {}
    default_url = targets.get("test_url") if isinstance(targets.get("test_url"), str) else None
    fetch_cfg = settings_json.get("fetch") if isinstance(settings_json.get("fetch"), dict) else {}

    use_proxy = request.try_proxy if request.try_proxy is not None else bool(fetch_cfg.get("use_proxy"))
    use_playwright = request.try_playwright if request.try_playwright is not None else bool(fetch_cfg.get("use_playwright"))
    timeout_s_raw = fetch_cfg.get("timeout_s")
    timeout_s = float(timeout_s_raw) if isinstance(timeout_s_raw, (int, float)) else float(getattr(db_source, "timeout_seconds", 15) or 15)
    headers = fetch_cfg.get("headers") if isinstance(fetch_cfg.get("headers"), dict) else None

    try:
        report = source_detect_service.detect_source(
            db=db,
            source=db_source,
            url_override=request.url or default_url,
            requested_url=request.url,
            use_proxy=use_proxy,
            use_playwright=use_playwright,
            timeout_s=timeout_s,
            headers=headers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Detect failed for source_id=%s: %s", source_id, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Detect failed")

    # Persist report for UI visibility
    settings = (db_source.settings_json or {}).copy()
    settings["detect_report"] = report
    settings["detected_strategy"] = report.get("detected_strategy")

    # Persist the chosen URL for downstream actions (Test Extract, Save Template, etc.)
    used_url = report.get("used_url") if isinstance(report.get("used_url"), str) else None
    if used_url:
        targets = settings.get("targets") if isinstance(settings.get("targets"), dict) else {}
        settings["targets"] = {**targets, "test_url": used_url}
    db_source.settings_json = settings
    db.add(db_source)
    db.commit()
    db.refresh(db_source)

    return report


class SourceTestExtractRequest(BaseModel):
    url: Optional[str] = None
    extract: Optional[dict] = None


@router.post("/sources/{source_id}/test-extract")
def test_extract(
    source_id: int,
    request: SourceTestExtractRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Test a generic HTML extractor config against a live page and return a preview.

    Config resolution:
      - Uses request.extract if provided
      - Else uses source.settings_json.extract

    Fetch uses httpx with proxy/playwright fallback if configured on the source.
    """
    db_source = service.get_source(db, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        return source_extract_service.test_extract(
            db=db,
            source=db_source,
            url_override=request.url,
            extract_override=request.extract,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Test extract failed for source_id=%s: %s", source_id, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Test extract failed")


class SourceSaveTemplateRequest(BaseModel):
    url: Optional[str] = None
    extract: Optional[dict] = None


@router.post("/sources/{source_id}/save-template")
def save_template(
    source_id: int,
    request: SourceSaveTemplateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Validate and save a generic HTML extractor template.

    - Runs the same extraction preview as /test-extract
    - If 0 items are found, returns 400 with helpful diagnostics
    - On success, merges into settings_json:
        - extract
        - targets.test_url
        - extract_sample (tested_at/url/items_preview)
        - detected_strategy (extract.strategy)
    """
    db_source = service.get_source(db, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    url_override = (request.url or "").strip() or None
    if request.url is not None and not url_override:
        raise HTTPException(status_code=400, detail="url must be a non-empty string when provided")

    try:
        preview = source_extract_service.test_extract(
            db=db,
            source=db_source,
            url_override=url_override,
            extract_override=request.extract if request.extract is not None else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Save template failed for source_id=%s: %s", source_id, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Save template failed")

    items_found = int(preview.get("items_found") or 0)
    items_preview = preview.get("items_preview") or []
    if not isinstance(items_preview, list):
        items_preview = []
    items_preview = items_preview[:5]

    if items_found <= 0:
        item_selector = None
        try:
            extract_used = request.extract if isinstance(request.extract, dict) else (db_source.settings_json or {}).get("extract") or {}
            list_cfg = extract_used.get("list") if isinstance(extract_used.get("list"), dict) else {}
            item_selector = list_cfg.get("item_selector")
        except Exception:
            item_selector = None

        detail = {
            "message": "No items found. Check your URL and CSS selectors (especially extract.list.item_selector).",
            "url": preview.get("used_url") or preview.get("url") or url_override,
            "item_selector": item_selector,
            "fetch": preview.get("fetch"),
            "errors": preview.get("errors") or [],
        }
        raise HTTPException(status_code=400, detail=detail)

    settings_json = db_source.settings_json or {}
    extract_used = request.extract if isinstance(request.extract, dict) else settings_json.get("extract")
    if not isinstance(extract_used, dict):
        raise HTTPException(status_code=400, detail="Missing extract config (provide body.extract or set source.settings_json.extract)")

    used_url = preview.get("used_url") if isinstance(preview.get("used_url"), str) else (preview.get("url") if isinstance(preview.get("url"), str) else (url_override or "").strip())
    if not used_url:
        raise HTTPException(status_code=400, detail="Missing URL (provide body.url or set source.settings_json.targets.test_url)")

    tested_at = datetime.utcnow().isoformat() + "Z"

    existing_settings = (db_source.settings_json or {}).copy()
    existing_targets = existing_settings.get("targets") if isinstance(existing_settings.get("targets"), dict) else {}

    patch_applied = {
        "extract": extract_used,
        "targets": {"test_url": used_url},
        "extract_sample": {
            "tested_at": tested_at,
            "url": used_url,
            "items_preview": items_preview,
        },
    }

    # Merge safely (avoid clobbering unrelated keys)
    next_settings = existing_settings.copy()
    next_settings["extract"] = extract_used
    next_settings["targets"] = {**existing_targets, "test_url": used_url}
    next_settings["extract_sample"] = patch_applied["extract_sample"]

    db_source.settings_json = next_settings
    db.add(db_source)
    db.commit()
    db.refresh(db_source)

    return {
        "saved": True,
        "items_found": items_found,
        "items_preview": items_preview,
        "settings_json_patch_applied": patch_applied,
        "requested_url": preview.get("requested_url"),
        "used_url": used_url,
        "fetch": preview.get("fetch"),
        "errors": preview.get("errors") or [],
    }


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Delete an admin data source (and cascade delete runs/items).

    Returns:
        - 204: Successfully deleted
        - 404: Source not found
        - 409: Cannot delete due to constraint violation (should not happen with CASCADE)
    """
    from sqlalchemy.exc import IntegrityError

    try:
        success = service.delete_source(db, source_id)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")
        return None
    except IntegrityError as e:
        # This should not happen with CASCADE constraints, but handle gracefully
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete source due to database constraint: {error_msg}. "
                   f"This may indicate missing CASCADE constraints. Please contact support."
        )


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

    # Attach proxy pool summary if using pool mode
    if db_source.proxy_mode == "pool":
        db_source.proxy_pool_summary = service.get_proxy_pool_summary(db)
    else:
        db_source.proxy_pool_summary = None

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
    try:
        from app.workers.data_engine import run_source_scrape
        task = run_source_scrape.delay(source_id)

        return {
            "task_id": task.id,
            "source_id": source_id,
            "message": "Scraping task enqueued"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue scraping task: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to enqueue scraping task. Celery worker may not be running. Error: {str(e)}"
        )


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


@router.post("/staged/{listing_id}/approve")
def approve_staged_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Approve a staged listing - merge it to merged_listings table.
    Copies listing data and attributes to merged_listings.
    """
    db_staged = service.get_staged_listing(db, listing_id)
    if not db_staged:
        raise HTTPException(status_code=404, detail="Staged listing not found")

    # Prepare listing data for merge
    listing_data = {
        "title": db_staged.title,
        "year": db_staged.year,
        "make": db_staged.make,
        "model": db_staged.model,
        "price_amount": db_staged.price_amount,
        "currency": db_staged.currency,
        "confidence_score": db_staged.confidence_score,
        "odometer_value": db_staged.odometer_value,
        "location": db_staged.location,
        "listed_at": db_staged.listed_at,
        "sale_datetime": db_staged.sale_datetime,
        "fetched_at": db_staged.fetched_at,
        "status": db_staged.status,
    }

    # Prepare attributes
    attributes = [
        {
            "key": attr.key,
            "value_text": attr.value_text,
            "value_num": attr.value_num,
            "value_bool": attr.value_bool,
            "unit": attr.unit,
        }
        for attr in db_staged.attributes
    ]

    # Upsert to merged_listings
    merged = service.upsert_merged_listing(
        db,
        source_key=db_staged.source_key,
        canonical_url=db_staged.canonical_url,
        listing_data=listing_data,
        attributes=attributes,
    )

    # Delete staged listing after merge
    db.delete(db_staged)
    db.commit()

    return {
        "success": True,
        "merged_listing_id": merged.id,
        "message": "Listing approved and merged"
    }


@router.post("/staged/{listing_id}/reject")
def reject_staged_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Reject a staged listing - delete it without merging.
    """
    db_staged = service.get_staged_listing(db, listing_id)
    if not db_staged:
        raise HTTPException(status_code=404, detail="Staged listing not found")

    db.delete(db_staged)
    db.commit()

    return {
        "success": True,
        "message": "Listing rejected and deleted"
    }


class BulkActionRequest(BaseModel):
    listing_ids: List[int]


@router.post("/staged/bulk-approve")
def bulk_approve_staged_listings(
    request: BulkActionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Bulk approve multiple staged listings.
    Merges all to merged_listings and deletes from staged.
    """
    approved = 0
    failed = 0
    errors = []

    for listing_id in request.listing_ids:
        try:
            db_staged = service.get_staged_listing(db, listing_id)
            if not db_staged:
                failed += 1
                errors.append(f"Listing {listing_id} not found")
                continue

            # Prepare and merge
            listing_data = {
                "title": db_staged.title,
                "year": db_staged.year,
                "make": db_staged.make,
                "model": db_staged.model,
                "price_amount": db_staged.price_amount,
                "currency": db_staged.currency,
                "confidence_score": db_staged.confidence_score,
                "odometer_value": db_staged.odometer_value,
                "location": db_staged.location,
                "listed_at": db_staged.listed_at,
                "sale_datetime": db_staged.sale_datetime,
                "fetched_at": db_staged.fetched_at,
                "status": db_staged.status,
            }

            attributes = [
                {
                    "key": attr.key,
                    "value_text": attr.value_text,
                    "value_num": attr.value_num,
                    "value_bool": attr.value_bool,
                    "unit": attr.unit,
                }
                for attr in db_staged.attributes
            ]

            service.upsert_merged_listing(
                db,
                source_key=db_staged.source_key,
                canonical_url=db_staged.canonical_url,
                listing_data=listing_data,
                attributes=attributes,
            )

            db.delete(db_staged)
            approved += 1

        except Exception as e:
            failed += 1
            errors.append(f"Listing {listing_id}: {str(e)}")
            logger.error(f"Failed to approve listing {listing_id}: {e}")

    db.commit()

    return {
        "success": True,
        "approved": approved,
        "failed": failed,
        "errors": errors if errors else None
    }


@router.post("/staged/bulk-reject")
def bulk_reject_staged_listings(
    request: BulkActionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Bulk reject multiple staged listings.
    Deletes all from staged without merging.
    """
    rejected = 0
    failed = 0
    errors = []

    for listing_id in request.listing_ids:
        try:
            db_staged = service.get_staged_listing(db, listing_id)
            if not db_staged:
                failed += 1
                errors.append(f"Listing {listing_id} not found")
                continue

            db.delete(db_staged)
            rejected += 1

        except Exception as e:
            failed += 1
            errors.append(f"Listing {listing_id}: {str(e)}")
            logger.error(f"Failed to reject listing {listing_id}: {e}")

    db.commit()

    return {
        "success": True,
        "rejected": rejected,
        "failed": failed,
        "errors": errors if errors else None
    }


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
