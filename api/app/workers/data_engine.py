"""
Data Engine Celery tasks for controlled scraping/importing.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session

from app.core.database import get_db_context
from app.services import data_engine_service as service
from app.services import crypto_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.data_engine.run_source_scrape")
def run_source_scrape(source_id: int) -> dict:
    """
    Execute a scraping run for a specific data source.

    Steps:
    1. Create AdminRun record (status=running)
    2. Fetch pages with rate limiting and pagination
    3. Extract items and store in staged_listings
    4. Update run status (succeeded/failed)
    5. Handle failures (increment failure_count, auto-disable)

    Returns dict with run_id, status, items_found, items_staged
    """
    with get_db_context() as db:
        # Get source
        source = service.get_source(db, source_id)
        if not source:
            logger.error(f"Source {source_id} not found")
            return {"error": "Source not found"}

        if not source.is_enabled:
            logger.info(f"Source {source_id} is disabled, skipping")
            return {"skipped": True, "reason": "Source disabled"}

        logger.info(f"Starting scrape run for source: {source.key}")

        # Create run record
        run = service.create_run(
            db,
            service.AdminRunCreate(
                source_id=source_id,
                status="running",
                started_at=datetime.utcnow(),
                pages_planned=source.max_pages_per_run,
                pages_done=0,
                items_found=0,
                items_staged=0,
            )
        )

        try:
            # Execute scraping
            result = _execute_scrape(db, source, run)

            # Update run as succeeded
            service.update_run(
                db,
                run.id,
                service.AdminRunUpdate(
                    status="succeeded",
                    finished_at=datetime.utcnow(),
                    pages_done=result["pages_done"],
                    items_found=result["items_found"],
                    items_staged=result["items_staged"],
                    debug_json=result.get("debug_info"),
                )
            )

            # Update source with success
            source.last_run_at = datetime.utcnow()
            source.next_run_at = datetime.utcnow() + timedelta(minutes=source.schedule_minutes)
            source.failure_count = 0
            source.disabled_reason = None
            db.commit()

            logger.info(
                f"Scrape run {run.id} succeeded: {result['items_found']} found, "
                f"{result['items_staged']} staged"
            )

            return {
                "run_id": run.id,
                "status": "succeeded",
                "items_found": result["items_found"],
                "items_staged": result["items_staged"],
            }

        except Exception as e:
            logger.error(f"Scrape run {run.id} failed: {e}", exc_info=True)

            # Update run as failed
            service.update_run(
                db,
                run.id,
                service.AdminRunUpdate(
                    status="failed",
                    finished_at=datetime.utcnow(),
                    error_summary=str(e)[:500],
                )
            )

            # Increment failure count and auto-disable if needed
            source.failure_count += 1
            source.last_run_at = datetime.utcnow()

            if source.failure_count >= 5:
                source.is_enabled = False
                source.disabled_reason = f"Auto-disabled after {source.failure_count} consecutive failures"
                logger.warning(f"Source {source.key} auto-disabled after {source.failure_count} failures")
            else:
                # Schedule retry with exponential backoff
                backoff_minutes = source.schedule_minutes * (2 ** (source.failure_count - 1))
                source.next_run_at = datetime.utcnow() + timedelta(minutes=min(backoff_minutes, 1440))

            db.commit()

            return {
                "run_id": run.id,
                "status": "failed",
                "error": str(e),
            }


def _execute_scrape(db: Session, source: Any, run: Any) -> dict:
    """
    Execute the actual scraping logic.

    For STEP 5 (list-only mode):
    - Fetch list pages only (no detail page follows)
    - Extract items from each page
    - Apply rate limiting and pagination
    - Use proxy if configured

    Returns dict with pages_done, items_found, items_staged, debug_info
    """
    pages_done = 0
    items_found = 0
    items_staged = 0
    debug_info = {}

    # Decrypt proxy settings if present
    settings_json = source.settings_json or {}
    if settings_json.get("proxy_enabled"):
        settings_json = service.decrypt_proxy_settings(settings_json)

    # Configure HTTP client with proxy and timeouts
    client_kwargs = {
        "timeout": httpx.Timeout(source.timeout_seconds),
        "follow_redirects": True,
    }

    if settings_json.get("proxy_enabled") and settings_json.get("proxy_url"):
        proxy_url = settings_json["proxy_url"]

        # Add auth to proxy URL if present
        if settings_json.get("proxy_username") and settings_json.get("proxy_password"):
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(proxy_url)
            proxy_url = urlunparse((
                parsed.scheme,
                f"{settings_json['proxy_username']}:{settings_json['proxy_password']}@{parsed.netloc}",
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))

        client_kwargs["proxies"] = {
            "http://": proxy_url,
            "https://": proxy_url,
        }
        debug_info["proxy_used"] = True

    # Rate limiting setup
    requests_per_second = source.rate_per_minute / 60.0
    min_delay = 1.0 / requests_per_second if requests_per_second > 0 else 0

    with httpx.Client(**client_kwargs) as client:
        # Fetch pages with pagination
        for page_num in range(1, source.max_pages_per_run + 1):
            try:
                # Build page URL with proper query param handling
                separator = "&" if "?" in source.base_url else "?"
                page_url = f"{source.base_url}{separator}page={page_num}"

                logger.info(f"Fetching page {page_num}/{source.max_pages_per_run}: {page_url}")

                # Rate limiting delay
                if pages_done > 0:
                    time.sleep(min_delay)

                # Fetch page
                start_time = time.time()
                response = client.get(page_url)
                response.raise_for_status()
                fetch_time = time.time() - start_time

                logger.debug(f"Page {page_num} fetched in {fetch_time:.2f}s (status {response.status_code})")

                pages_done += 1

                # Parse items from page (placeholder - actual parsing depends on source)
                # For STEP 5, we'll just create a simple parser
                page_items = _parse_list_page(response.text, source.key)
                items_found += len(page_items)

                # Store items in staged_listings (with auto-merge check)
                for item_data in page_items:
                    try:
                        # Upsert to staging
                        staged = service.upsert_staged_listing(
                            db,
                            run_id=run.id,
                            source_key=source.key,
                            canonical_url=item_data["canonical_url"],
                            listing_data=item_data["listing"],
                            attributes=item_data.get("attributes"),
                        )
                        items_staged += 1

                        # Check auto-merge rules
                        should_merge, reason = service.should_auto_merge(db, source, staged)
                        if should_merge:
                            service.auto_merge_listing(db, staged)
                            debug_info["auto_merged"] = debug_info.get("auto_merged", 0) + 1
                            logger.debug(f"Auto-merged: {staged.canonical_url}")
                        else:
                            debug_info.setdefault("manual_review_reasons", {})[reason] = \
                                debug_info.get("manual_review_reasons", {}).get(reason, 0) + 1
                            logger.debug(f"Manual review required: {reason}")

                    except Exception as e:
                        logger.error(f"Failed to stage item: {e}")

                # Check if we've hit max items limit
                if items_staged >= source.max_items_per_run:
                    logger.info(f"Reached max_items_per_run ({source.max_items_per_run}), stopping")
                    break

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on page {page_num}: {e}")
                if e.response.status_code == 404:
                    # No more pages, stop pagination
                    logger.info("Got 404, assuming end of pagination")
                    break
                else:
                    raise
            except Exception as e:
                logger.error(f"Error fetching page {page_num}: {e}")
                raise

    debug_info.update({
        "pages_done": pages_done,
        "items_found": items_found,
        "items_staged": items_staged,
        "avg_items_per_page": items_found / pages_done if pages_done > 0 else 0,
    })

    return {
        "pages_done": pages_done,
        "items_found": items_found,
        "items_staged": items_staged,
        "debug_info": debug_info,
    }


def _parse_list_page(html: str, source_key: str) -> list[dict]:
    """
    Parse items from a list page HTML.

    This is a placeholder parser that returns empty list.
    Real implementation would use BeautifulSoup/lxml to extract items.

    For STEP 5, actual parsing logic will be source-specific.
    """
    # TODO: Implement source-specific parsers
    # For now, return empty list (no items extracted)

    logger.warning(f"Using placeholder parser for {source_key} - no items will be extracted")
    return []


@celery_app.task(name="app.workers.data_engine.enqueue_due_sources")
def enqueue_due_sources() -> dict:
    """
    Scheduler task: enqueue scraping for all due sources.

    Called periodically by Celery Beat.
    Finds sources where next_run_at <= now and is_enabled=True.
    Enqueues run_source_scrape task for each.
    """
    with get_db_context() as db:
        due_sources = service.get_due_sources(db)

        enqueued = 0
        for source in due_sources:
            logger.info(f"Enqueueing scrape for source: {source.key}")
            run_source_scrape.delay(source.id)
            enqueued += 1

        logger.info(f"Enqueued {enqueued} data source scrapes")
        return {"enqueued": enqueued}
