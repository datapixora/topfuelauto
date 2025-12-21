from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Optional, Set
import logging

from fastapi import HTTPException, Response

from app.schemas import auction as schemas
from app.services import proxy_service
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _test_parse_sync(
    request: schemas.BidfaxTestParseRequest,
    response: Response,
    db,
    admin,
    request_id: str,
    start_time: float,
):
    from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider

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

    def _healthy_proxies(exclude_ids: Optional[Set[int]] = None, require_ok_status: bool = True):
        """Get healthy, non-banned proxies. Optionally filter by last_check_status='ok'."""
        now = datetime.now(timezone.utc)
        exclude = exclude_ids or set()
        healthy = []
        for p in proxy_service.list_enabled_proxies(db):
            if p.id in exclude:
                continue

            # Skip if banned
            if p.banned_until:
                banned = p.banned_until
                if banned.tzinfo is None:
                    banned = banned.replace(tzinfo=timezone.utc)
                if banned > now:
                    continue

            # Skip if unhealthy
            u = p.unhealthy_until
            if u is not None:
                if u.tzinfo is None:
                    u = u.replace(tzinfo=timezone.utc)
                if u > now:
                    continue

            # Skip if not in "ok" status (when required)
            if require_ok_status and p.last_check_status != "ok":
                continue

            healthy.append(p)
        return healthy

    def _refresh_smartproxy_pool():
        """Refresh proxy pool from Smartproxy API."""
        try:
            from app.services.smartproxy_service import SmartproxyAPI, sync_smartproxy_to_db
            logger.info("Auto-refreshing Smartproxy pool due to no healthy proxies...")
            api = SmartproxyAPI()
            proxies = api.fetch_proxies()
            stats = sync_smartproxy_to_db(db, proxies)
            logger.info(f"Smartproxy auto-refresh: {stats['created']} created, {stats['updated']} updated")
            return stats
        except Exception as e:
            logger.error(f"Failed to auto-refresh Smartproxy pool: {e}")
            return None

    # Validate fetch_mode
    if fetch_mode not in ("http", "browser"):
        return fail_response("INVALID_FETCH_MODE", "validate", f"Invalid fetch_mode: {fetch_mode}")

    logger.info(
        "STAGE_START proxy_select",
        extra={"request_id": request_id, "url": request.url, "fetch_mode": fetch_mode},
    )

    # Build proxy candidate list - try ALL healthy proxies with "ok" status
    proxy_candidates = []
    if proxy_id:
        # User selected a specific proxy - try it first, then fall back to others
        proxy = proxy_service.get_proxy(db, proxy_id)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")
        proxy_candidates.append(proxy)
        # Add all other healthy proxies as fallbacks
        proxy_candidates.extend(_healthy_proxies({proxy.id}, require_ok_status=True))
    else:
        # Get ALL healthy proxies with "ok" status
        proxy_candidates = _healthy_proxies(require_ok_status=True)

    # If no healthy proxies with "ok" status, try to refresh from Smartproxy
    if not proxy_candidates:
        logger.warning("No healthy proxies with 'ok' status found, attempting Smartproxy refresh...")
        refresh_result = _refresh_smartproxy_pool()
        if refresh_result:
            # Try again after refresh
            proxy_candidates = _healthy_proxies(require_ok_status=False)  # Be less strict after refresh

    logger.info(f"Found {len(proxy_candidates)} proxy candidates to try")

    proxy_check_result = None
    if proxy_candidates:
        logger.info(
            "STAGE_START proxy_check",
            extra={"request_id": request_id, "url": request.url, "fetch_mode": fetch_mode, "candidates": len(proxy_candidates)},
        )

    # Try ALL proxy candidates until one works
    for idx, candidate in enumerate(proxy_candidates):
        proxy_used = True
        proxy_name = candidate.name
        proxy_url_candidate = proxy_service.build_proxy_url(candidate)

        logger.info(f"Trying proxy {idx+1}/{len(proxy_candidates)}: {proxy_name} (id={candidate.id})")

        proxy_check_result = proxy_service.check_proxy(db, candidate)
        proxy_stage = proxy_check_result.get("stage")
        proxy_error_code = proxy_check_result.get("error_code")
        candidate_exit_ip = proxy_check_result.get("exit_ip")
        if candidate_exit_ip:
            proxy_exit_ip = candidate_exit_ip

        if proxy_check_result.get("ok"):
            chosen_proxy = candidate
            proxy_url = proxy_url_candidate
            logger.info(f"Proxy {proxy_name} passed health check, using it")
            break
        else:
            logger.warning(f"Proxy {proxy_name} failed: {proxy_check_result.get('error')}")

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
        logger.info(
            "STAGE_END proxy_check",
            extra={"request_id": request_id, "status": "fail", "code": code},
        )
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

    logger.info(
        "STAGE_START fetch",
        extra={
            "request_id": request_id,
            "url": request.url,
            "fetch_mode": fetch_mode,
            "proxy_id": chosen_proxy.id if chosen_proxy else proxy_id,
        },
    )

    if fetch_mode == "browser":
        # Cap browser timeout
        provider.browser_fetcher.timeout_ms = min(provider.browser_fetcher.timeout_ms, 18000)

    fetch_kwargs = {}
    if fetch_mode == "http":
        fetch_kwargs["timeout"] = 12.0

    fetch_result = provider.fetch_list_page(
        url=request.url,
        proxy_url=proxy_url,
        proxy_id=chosen_proxy.id if chosen_proxy else proxy_id,
        fetch_mode=fetch_mode,
        **fetch_kwargs,
    )

    # Update diagnostics from fetch result
    http_status = fetch_result.status_code or 0
    latency_ms = fetch_result.latency_ms
    http_error = fetch_result.error
    if fetch_result.proxy_exit_ip:
        proxy_exit_ip = fetch_result.proxy_exit_ip

    if fetch_result.error or not fetch_result.html:
        message = http_error or "Fetch returned empty HTML"
        if http_status == 403 and not proxy_used:
            message += " (blocked; try using a proxy)"
        code = "EMPTY_HTML" if not fetch_result.html else proxy_error_code
        logger.info(
            "STAGE_END fetch",
            extra={"request_id": request_id, "status": "fail", "code": code},
        )
        return fail_response(code, f"fetch_{fetch_mode}", message, http_status=http_status, latency_ms=latency_ms)

    logger.info(
        "STAGE_END fetch",
        extra={"request_id": request_id, "status": "ok", "latency_ms": latency_ms},
    )

    logger.info(
        "STAGE_START parse",
        extra={"request_id": request_id, "url": request.url},
    )
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
        "STAGE_END parse",
        extra={"request_id": request_id, "status": "ok", "items": len(results)},
    )

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
