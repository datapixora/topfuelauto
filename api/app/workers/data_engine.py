"""
Data Engine Celery tasks for controlled scraping/importing.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import httpx
import random
from sqlalchemy.orm import Session
import os

from app.core.database import get_db_context
from app.services import data_engine_service as service
from app.services import proxy_service
from app.services import crypto_service
from app.schemas import data_engine as schemas
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class BlockedResponseError(Exception):
    """Raised when a page clearly indicates bot-block/Incapsula/Imperva."""


def _detect_block(response: httpx.Response, html: str) -> Tuple[bool, Optional[str]]:
    """
    Lightweight bot-block detection (no bypass).
    Conditions:
      - Contains '_Incapsula_Resource' or 'imperva'
      - meta robots noindex with tiny body
      - html length < 1000
    """
    html_len = len(html or "")
    lower = html.lower() if html else ""

    if "_incapsula_resource" in lower:
        return True, "incapsula"
    if "imperva" in lower:
        return True, "imperva"
    if "noindex" in lower and html_len < 1200:
        return True, "robots_noindex"
    if html_len < 1000:
        return True, "html_too_short"

    return False, None


def _diagnostic_payload(response: httpx.Response, blocked: bool, block_reason: Optional[str], proxy_used: bool) -> Dict[str, Any]:
    return {
        "status_code": response.status_code,
        "final_url": str(response.url),
        "html_len": len(response.text or ""),
        "blocked": blocked,
        "block_reason": block_reason,
        "proxy_used": proxy_used,
    }


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    prefix = value.split("-", 1)[0][:4]
    return f"{prefix}***"


def _build_proxy_from_env() -> Tuple[Optional[str], Dict[str, Any]]:
    host = os.getenv("PROXY_HOST", "proxy.smartproxy.net")
    port = os.getenv("PROXY_PORT", "3120")
    user = os.getenv("PROXY_USERNAME")
    pwd = os.getenv("PROXY_PASSWORD")
    scheme = os.getenv("PROXY_SCHEME", "http")

    if not user or not pwd:
        return None, {}

    proxy_url = f"{scheme}://{user}:{pwd}@{host}:{port}"
    meta = {
        "proxy_host": host,
        "proxy_port": port,
        "proxy_username_masked": _mask_secret(user),
    }
    return proxy_url, meta


def check_proxy(proxy_url: str) -> Dict[str, Any]:
    """Call ipify via proxy to sanity check."""
    try:
        with httpx.Client(proxy=proxy_url, timeout=10.0, verify=False) as client:
            resp = client.get("https://api.ipify.org", params={"format": "json"})
            return {
                "ok": resp.status_code == 200,
                "status_code": resp.status_code,
                "body_len": len(resp.text or ""),
                "ip": resp.json().get("ip") if resp.headers.get("content-type", "").startswith("application/json") else None,
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


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

        proxy_for_run = proxy_service.select_proxy_for_run(db)
        proxy_id = proxy_for_run.id if proxy_for_run else None

        # Create run record
        run = service.create_run(
            db,
            schemas.AdminRunCreate(
                source_id=source_id,
                status="running",
                started_at=datetime.utcnow(),
                pages_planned=source.max_pages_per_run,
                pages_done=0,
                items_found=0,
                items_staged=0,
                proxy_id=proxy_id,
            )
        )

        try:
            # Execute scraping
            result = _execute_scrape(db, source, run, proxy_for_run)

            if result.get("blocked"):
                # Mark as blocked (not a success)
                service.update_run(
                    db,
                    run.id,
                    schemas.AdminRunUpdate(
                        status="blocked",
                        finished_at=datetime.utcnow(),
                        pages_done=result.get("pages_done", 0),
                        items_found=result.get("items_found", 0),
                        items_staged=result.get("items_staged", 0),
                        error_summary="Blocked by bot protection",
                        debug_json=result.get("debug_info"),
                    ),
                )
                source.last_run_at = datetime.utcnow()
                service.record_block_event(db, source, result.get("block_reason") or "blocked", result.get("diagnostics") or {})
                db.commit()

                logger.warning(
                    f"Scrape run {run.id} blocked by bot protection: {result.get('block_reason')}"
                )

                return {
                    "run_id": run.id,
                    "status": "blocked",
                    "block_reason": result.get("block_reason"),
                    "diagnostics": result.get("diagnostics"),
                    "proxy_exit_ip": result.get("proxy_exit_ip"),
                }

            if result.get("proxy_failed"):
                service.update_run(
                    db,
                    run.id,
                    schemas.AdminRunUpdate(
                        status="proxy_failed",
                        finished_at=datetime.utcnow(),
                        pages_done=result.get("pages_done", 0),
                        items_found=result.get("items_found", 0),
                        items_staged=result.get("items_staged", 0),
                        error_summary=result.get("error")[:500] if result.get("error") else "Proxy failed",
                        debug_json=result.get("debug_info"),
                        proxy_exit_ip=result.get("proxy_exit_ip"),
                        proxy_error=result.get("error"),
                    ),
                )
                source.last_run_at = datetime.utcnow()
                if proxy_for_run:
                    proxy_service.record_proxy_failure(db, proxy_for_run, result.get("error") or "proxy error")
                service.record_proxy_failure(db, source, result.get("error") or "proxy error")
                db.commit()

                logger.warning(
                    f"Scrape run {run.id} failed due to proxy: {result.get('error')}"
                )

                return {
                    "run_id": run.id,
                    "status": "proxy_failed",
                    "error": result.get("error"),
                    "diagnostics": result.get("diagnostics"),
                    "proxy_exit_ip": result.get("proxy_exit_ip"),
                }

            # Update run as succeeded
                service.update_run(
                    db,
                    run.id,
                    schemas.AdminRunUpdate(
                        status="succeeded",
                        finished_at=datetime.utcnow(),
                        pages_done=result["pages_done"],
                        items_found=result["items_found"],
                        items_staged=result["items_staged"],
                        debug_json=result.get("debug_info"),
                        proxy_exit_ip=result.get("proxy_exit_ip"),
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
                "proxy_exit_ip": result.get("proxy_exit_ip"),
            }

        except Exception as e:
            logger.error(f"Scrape run {run.id} failed: {e}", exc_info=True)

            # Update run as failed
            service.update_run(
                db,
                run.id,
                schemas.AdminRunUpdate(
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


def _execute_scrape(db: Session, source: Any, run: Any, proxy: Any = None) -> dict:
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
    proxy_used = False
    proxy_meta = {}
    proxy_exit_ip = None

    # Lightweight UA rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]

    client_kwargs = {
        "timeout": httpx.Timeout(source.timeout_seconds),
        "follow_redirects": True,
    }

    proxy_url = None
    if proxy:
        proxy_url = proxy_service.build_proxy_url(proxy)
        proxy_meta = {
            "proxy_host": proxy.host,
            "proxy_port": proxy.port,
            "proxy_username_masked": proxy_service.mask_username(proxy.username),
        }
    else:
        # Fallback to env-based proxy if no DB proxy
        env_proxy_url, env_meta = _build_proxy_from_env()
        if env_proxy_url:
            proxy_url = env_proxy_url
            proxy_meta = env_meta

    if proxy_url:
        client_kwargs["proxy"] = proxy_url
        proxy_used = True
        debug_info["proxy_used"] = True
        debug_info["proxy"] = {k: v for k, v in proxy_meta.items() if v}

        if (settings_json.get("debug_proxy_check") or os.getenv("DATA_ENGINE_DEBUG_PROXY") == "1"):
            check = check_proxy(proxy_url)
            debug_info["proxy_check"] = check
            if check.get("ip"):
                proxy_exit_ip = check["ip"]

    # Rate limiting setup
    requests_per_second = source.rate_per_minute / 60.0
    min_delay = 1.0 / requests_per_second if requests_per_second > 0 else 0

    # In-memory cache to avoid duplicate fetches in a short window
    CACHE_TTL_SECONDS = 10 * 60
    global SIGNATURE_CACHE  # defined below
    if "SIGNATURE_CACHE" not in globals():
        SIGNATURE_CACHE = {}

    with httpx.Client(**client_kwargs) as client:
        # Fetch pages with pagination
        for page_num in range(1, source.max_pages_per_run + 1):
            try:
                # Build page URL with proper query param handling
                separator = "&" if "?" in source.base_url else "?"
                page_url = f"{source.base_url}{separator}page={page_num}"
                signature = f"{source.key}:{page_url}"

                logger.info(f"Fetching page {page_num}/{source.max_pages_per_run}: {page_url}")

                cache_entry = SIGNATURE_CACHE.get(signature)
                cache_hit = False
                if cache_entry:
                    ts, cached_items, cached_diagnostics = cache_entry
                    if time.time() - ts <= CACHE_TTL_SECONDS:
                        cache_hit = True
                        logger.info(f"Cache hit for {signature}, skipping fetch")
                        diagnostics = {**cached_diagnostics, "cache_hit": True}
                        debug_info.setdefault("pages", []).append({"page": page_num, **diagnostics})
                        page_items = cached_items
                    else:
                        SIGNATURE_CACHE.pop(signature, None)

                if not cache_hit:
                    # Rate limiting delay
                    if pages_done > 0:
                        time.sleep(min_delay)

                    # Fetch page
                    start_time = time.time()
                    headers = {
                        "User-Agent": random.choice(user_agents),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Cache-Control": "max-age=0",
                    }
                    response = client.get(page_url, headers=headers)
                    response.raise_for_status()
                    fetch_time = time.time() - start_time

                    logger.debug(f"Page {page_num} fetched in {fetch_time:.2f}s (status {response.status_code})")

                    pages_done += 1

                    # Bot-block detection
                    html = response.text
                    blocked, block_reason = _detect_block(response, html)
                    diagnostics = _diagnostic_payload(response, blocked, block_reason, proxy_used)
                    diagnostics["cache_hit"] = False
                    debug_info.setdefault("pages", []).append(
                        {"page": page_num, **diagnostics}
                    )
                    if blocked:
                        logger.warning(f"Blocked by bot protection on page {page_num}: {block_reason}")
                    return {
                        "blocked": True,
                        "block_reason": block_reason,
                        "pages_done": pages_done,
                        "items_found": items_found,
                        "items_staged": items_staged,
                        "debug_info": {**debug_info, "block_reason": block_reason},
                        "diagnostics": diagnostics,
                        "proxy_exit_ip": proxy_exit_ip,
                    }

                    # Parse items from page
                    page_items = _parse_list_page(html, source.key)

                    # Only cache non-blocked results with reasonable length
                    if len(html or "") >= 1000:
                        SIGNATURE_CACHE[signature] = (time.time(), page_items, diagnostics)

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

                        # Check auto-merge rules (auto-approve, still manual merge trigger)
                        should_merge, reason = service.should_auto_merge(db, source, staged)
                        staged.auto_approved = should_merge
                        db.add(staged)
                        db.commit()

                        if should_merge:
                            debug_info["auto_approved"] = debug_info.get("auto_approved", 0) + 1
                            logger.debug(f"Auto-approved for merge: {staged.canonical_url}")
                        else:
                            reason_key = reason or "manual_review"
                            debug_info.setdefault("manual_review_reasons", {})[reason_key] = \
                                debug_info.get("manual_review_reasons", {}).get(reason_key, 0) + 1
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
            except httpx.ProxyError as e:
                logger.error(f"Proxy error on page {page_num}: {e}")
                diagnostics = {
                    "proxy_used": proxy_used,
                    "proxy_host": proxy_meta.get("proxy_host"),
                    "proxy_port": proxy_meta.get("proxy_port"),
                    "error": str(e),
                }
                debug_info.setdefault("pages", []).append(
                    {"page": page_num, "proxy_failed": True, **diagnostics}
                )
                return {
                    "proxy_failed": True,
                    "error": str(e),
                    "diagnostics": diagnostics,
                    "pages_done": pages_done,
                    "items_found": items_found,
                    "items_staged": items_staged,
                    "debug_info": debug_info,
                    "proxy_exit_ip": proxy_exit_ip,
                }
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
        "proxy_exit_ip": proxy_exit_ip,
    }


def _parse_list_page(html: str, source_key: str) -> list[dict]:
    """
    Parse items from a list page HTML using BeautifulSoup.

    Returns list of dicts with structure:
    {
        "canonical_url": "https://...",  # Required: unique URL for this listing
        "listing": {                      # Required: listing data fields
            "title": "...",
            "year": 2020,
            "make": "Toyota",
            "model": "Camry",
            "price_amount": 15000.00,
            "currency": "USD",
            # ... other fields
        },
        "attributes": [                   # Optional: additional key-value data
            {"key": "vin", "value_text": "..."},
            {"key": "mileage", "value_num": 50000, "unit": "miles"},
        ]
    }
    """
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(html, 'lxml')
        items = []

        # Debug: Log HTML snippet to verify content
        html_preview = html[:500] if html else "NO HTML"
        logger.info(f"HTML preview for {source_key}: {html_preview}")
        logger.info(f"HTML length: {len(html)} characters")

        # ============================================================================
        # CUSTOMIZE THIS SECTION FOR YOUR SOURCE
        # ============================================================================

        # Step 1: Find all listing containers
        # Common patterns:
        # - soup.find_all('div', class_='listing-item')
        # - soup.find_all('article', class_='vehicle-card')
        # - soup.select('.results .item')

        listing_elements = soup.find_all('div', class_='listing-item')  # ← CUSTOMIZE THIS

        logger.info(f"Found {len(listing_elements)} listing elements on page")

        for element in listing_elements:
            try:
                # Step 2: Extract the canonical URL (required)
                # Common patterns:
                # - element.find('a', class_='title')['href']
                # - element.select_one('.vehicle-link')['href']
                # - element.find('a')['href']

                link_tag = element.find('a', class_='item-link')  # ← CUSTOMIZE THIS
                if not link_tag or not link_tag.get('href'):
                    continue

                canonical_url = link_tag['href']
                # Make URL absolute if needed
                if canonical_url.startswith('/'):
                    # Extract base domain from first occurrence
                    canonical_url = f"https://www.example.com{canonical_url}"  # ← CUSTOMIZE DOMAIN

                # Step 3: Extract listing fields
                # Use helper methods like .find(), .select_one(), .get_text()

                title = element.find('h3', class_='title')
                title_text = title.get_text(strip=True) if title else None

                price = element.find('span', class_='price')
                price_text = price.get_text(strip=True) if price else None
                price_amount = _extract_number(price_text) if price_text else None

                year_tag = element.find('span', class_='year')
                year = int(year_tag.get_text(strip=True)) if year_tag else None

                make_tag = element.find('span', class_='make')
                make = make_tag.get_text(strip=True) if make_tag else None

                model_tag = element.find('span', class_='model')
                model = model_tag.get_text(strip=True) if model_tag else None

                # Step 4: Build listing data dict
                listing_data = {
                    "title": title_text,
                    "year": year,
                    "make": make,
                    "model": model,
                    "price_amount": price_amount,
                    "currency": "USD",
                    "confidence_score": 1.0,
                    "status": "active",
                }

                # Step 5: Extract additional attributes (optional)
                attributes = []

                # Example: VIN
                vin_tag = element.find('span', class_='vin')
                if vin_tag:
                    attributes.append({
                        "key": "vin",
                        "value_text": vin_tag.get_text(strip=True),
                    })

                # Example: Mileage
                mileage_tag = element.find('span', class_='mileage')
                if mileage_tag:
                    mileage_num = _extract_number(mileage_tag.get_text(strip=True))
                    if mileage_num:
                        attributes.append({
                            "key": "odometer",
                            "value_num": mileage_num,
                            "unit": "miles",
                        })

                # Step 6: Add to results
                items.append({
                    "canonical_url": canonical_url,
                    "listing": listing_data,
                    "attributes": attributes if attributes else None,
                })

            except Exception as e:
                logger.warning(f"Failed to parse listing element: {e}")
                continue

        logger.info(f"Successfully parsed {len(items)} items from page")
        return items

    except Exception as e:
        logger.error(f"Failed to parse HTML for {source_key}: {e}", exc_info=True)
        return []


def _extract_number(text: str) -> float | None:
    """
    Extract first number from text string.
    Examples: "$15,000" → 15000.0, "50k miles" → 50000.0
    """
    if not text:
        return None

    import re
    # Remove common currency symbols and commas
    cleaned = re.sub(r'[$,€£¥]', '', text)

    # Handle "k" suffix (thousands)
    if 'k' in cleaned.lower():
        match = re.search(r'([\d.]+)\s*k', cleaned.lower())
        if match:
            return float(match.group(1)) * 1000

    # Extract first number (int or float)
    match = re.search(r'[\d,]+\.?\d*', cleaned)
    if match:
        return float(match.group().replace(',', ''))

    return None


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
