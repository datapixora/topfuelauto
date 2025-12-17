import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_optional_user
from app.models.search_field import SearchField
import logging

from app.providers import get_active_providers
from app.schemas import search as search_schema
from app.services import (
    search_service,
    usage_service,
    plan_service,
    provider_setting_service,
    search_cache_service,
    query_parser,
    search_job_service,
)
from app.workers.search_crawl import run_on_demand_crawl

router = APIRouter(prefix="/api/v1", tags=["search"])

CACHE_TTL_SECONDS = 45
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60
DEFAULT_FREE_SEARCHES_PER_DAY = 5

_search_cache: Dict[str, Tuple[float, search_schema.SearchResponse]] = {}
_rate_limit: Dict[str, list[float]] = defaultdict(list)


def _should_execute_provider(provider, filters: Dict[str, Any]) -> Tuple[bool, str | None]:
    """
    Determine if a provider should be executed based on filters and capabilities.

    Returns: (should_execute, skip_reason)
    """
    # Check if provider requires structured filters (make/model)
    requires_structured = getattr(provider, "requires_structured", False)
    has_structured = filters.get("make") or filters.get("model")

    if requires_structured and not has_structured:
        return False, "requires_structured_filters"

    return True, None


def _make_cache_key(
    ip: str,
    q: str,
    make: str | None,
    model: str | None,
    year_min: int | None,
    year_max: int | None,
    price_min: int | None,
    price_max: int | None,
    location: str | None,
    sort: str | None,
    page: int,
    page_size: int,
) -> str:
    return "|".join(
        [
            ip,
            q,
            make or "",
            model or "",
            str(year_min or ""),
            str(year_max or ""),
            str(price_min or ""),
            str(price_max or ""),
            location or "",
            sort or "",
            str(page),
            str(page_size),
        ]
    )


def _check_rate_limit(ip: str):
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    events = _rate_limit[ip]
    _rate_limit[ip] = [t for t in events if t >= window_start]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    _rate_limit[ip].append(now)


@router.get("/search", response_model=search_schema.SearchResponse)
def search(
    response: Response,
    request: Request,
    q: str = Query(..., min_length=1),
    deep: bool = Query(False, description="Trigger on-demand crawl"),
    make: str | None = None,
    model: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    location: str | None = None,
    sort: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    request_id = str(uuid.uuid4())
    response.headers["X-Request-Id"] = request_id

    client_ip = request.client.host if request.client else "unknown"
    session_id = request.headers.get("X-Session-Id")
    session_id = session_id[:64] if session_id else None
    query_raw = q

    # Parse query to extract structured filters
    query_normalized, parsed_filters = query_parser.parse_query(q, make, model)

    # Priority: explicit UI fields override parsed values
    filters = {
        "make": make or parsed_filters.get("make"),
        "model": model or parsed_filters.get("model"),
        "year_min": year_min,
        "year_max": year_max,
        "price_min": price_min,
        "price_max": price_max,
        "location": location,
        "sort": sort,
    }

    try:
        _check_rate_limit(client_ip)
    except HTTPException:
        try:
            search_service.log_search_event(
                db,
                user_id=user_id,
                session_id=session_id,
                query_raw=query_raw,
                query_normalized=query_normalized,
                filters=filters,
                providers=[],
                result_count=0,
                latency_ms=0,
                cache_hit=False,
                rate_limited=True,
                status="error",
                error_code="rate_limited",
            )
        finally:
            response.headers["X-Cache"] = "MISS"
        raise

    user_id = getattr(current_user, "id", None) if current_user else None

    # Plan + quota resolution (only for authenticated users)
    plan_limit = None
    quota_message = "Daily search limit reached. Upgrade to continue."
    active_plan = None
    if current_user:
        active_plan = plan_service.get_active_plan(db, current_user)
        if active_plan and active_plan.searches_per_day is not None:
            plan_limit = active_plan.searches_per_day
        elif active_plan and active_plan.key == "free":
            plan_limit = DEFAULT_FREE_SEARCHES_PER_DAY  # fail-safe default for free if plan config missing
        elif not active_plan:
            plan_limit = DEFAULT_FREE_SEARCHES_PER_DAY
        if active_plan and active_plan.quota_reached_message:
            quota_message = active_plan.quota_reached_message

    if current_user and plan_limit is not None:
        usage = usage_service.get_or_create_today_usage(db, current_user.id)
        if usage.search_count >= plan_limit:
            reset_at = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            payload = {
                "detail": quota_message,
                "code": "quota_exceeded",
                "limit": plan_limit,
                "used": usage.search_count,
                "remaining": max(plan_limit - usage.search_count, 0),
                "reset_at": reset_at.isoformat(),
            }
            try:
                search_service.log_search_event(
                    db,
                    user_id=user_id,
                    session_id=session_id,
                    query_raw=query_raw,
                    query_normalized=query_normalized,
                    filters=filters,
                    providers=[],
                    result_count=0,
                    latency_ms=None,
                    cache_hit=False,
                    rate_limited=False,
                    status="error",
                    error_code="quota_exceeded",
                )
            except Exception:
                pass
            resp = JSONResponse(status_code=429, content=payload)
            resp.headers["X-Cache"] = "MISS"
            return resp

    settings = get_settings()
    # Load enabled providers from DB - NO hardcoded exclusions!
    enabled_keys = provider_setting_service.get_enabled_providers(db, "search")
    # Get all provider enabled/disabled states for proper reporting
    provider_states = provider_setting_service.get_provider_states(db, "search")
    web_crawl_setting = provider_setting_service.get_setting(db, "web_crawl_on_demand")
    web_crawl_config = web_crawl_setting.settings_json if web_crawl_setting else {}
    crawl_allowlist = (web_crawl_config.get("allowlist") if isinstance(web_crawl_config, dict) else None) or settings.crawl_search_allowlist
    crawl_min_results = (
        web_crawl_config.get("min_results")
        if isinstance(web_crawl_config, dict) and web_crawl_config.get("min_results") is not None
        else settings.crawl_search_min_results
    )
    if web_crawl_setting and web_crawl_setting.enabled and crawl_allowlist and "web_crawl_on_demand" not in enabled_keys:
        enabled_keys.append("web_crawl_on_demand")

    # Build providers from DB-enabled keys only (respects admin settings)
    providers = get_active_providers(settings, allowed_keys=enabled_keys, config_map={"web_crawl_on_demand": web_crawl_config})

    # NO failsafe to marketcheck - respect admin DB settings completely
    # If admin disables all providers, return empty results (not force marketcheck)

    # Use final filters (after priority override) for cache key
    cache_key = _make_cache_key(
        client_ip,
        query_normalized,
        filters.get("make"),
        filters.get("model"),
        year_min,
        year_max,
        price_min,
        price_max,
        location,
        sort,
        page,
        page_size,
    )
    cached = _search_cache.get(cache_key) if not deep else None
    now = time.time()
    if cached and now - cached[0] <= CACHE_TTL_SECONDS:
        response.headers["X-Cache"] = "HIT"
        quota_info = None
        try:
            usage = None
            if current_user:
                usage = usage_service.get_or_create_today_usage(db, current_user.id)
                remaining = None
                if plan_limit is not None:
                    remaining = max(plan_limit - usage.search_count, 0)
                quota_info = search_schema.SearchQuota(
                    limit=plan_limit,
                    used=usage.search_count,
                    remaining=remaining,
                    reset_at=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                    if plan_limit is not None
                    else None,
                )
            search_service.log_search_event(
                db,
                user_id=user_id,
                session_id=session_id,
                query_raw=query_raw,
                query_normalized=query_normalized,
                filters=filters,
                providers=[s.get("name") for s in cached[1].sources if s],
                result_count=cached[1].total,
                latency_ms=None,
                cache_hit=True,
                rate_limited=False,
                status="ok",
                error_code=None,
            )
        except Exception:
            pass
        cached_response = cached[1].copy()
        cached_response.quota = quota_info
        _search_cache[cache_key] = (now, cached_response)
        return cached_response

    # DB cache
    signature = search_cache_service.compute_signature(enabled_keys, query_normalized, filters, page, page_size)
    cached_db = None
    if not deep:
        try:
            cached_db = search_cache_service.get_cached(db, signature, ttl_minutes=15)
        except Exception as exc:
            db.rollback()
            logging.getLogger(__name__).warning("search cache get failed: %s", exc)
            cached_db = None

    if cached_db:
        response.headers["X-Cache"] = "HIT"
        quota_info = None
        if current_user:
            usage = usage_service.get_or_create_today_usage(db, current_user.id)
            remaining = None
            if plan_limit is not None:
                remaining = max(plan_limit - usage.search_count, 0)
            quota_info = search_schema.SearchQuota(
                limit=plan_limit,
                used=usage.search_count,
                remaining=remaining,
                reset_at=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                if plan_limit is not None
                else None,
            )
        try:
            search_service.log_search_event(
                db,
                user_id=user_id,
                session_id=session_id,
                query_raw=query_raw,
                query_normalized=query_normalized,
                filters=filters,
                providers=cached_db.providers_json or enabled_keys,
                result_count=cached_db.total or 0,
                latency_ms=None,
                cache_hit=True,
                rate_limited=False,
                status="ok",
                error_code=None,
            )
        except Exception:
            pass

        # Build sources list respecting current provider states
        cached_providers = cached_db.providers_json or enabled_keys or []
        sources_list = []
        for p in cached_providers:
            is_enabled = provider_states.get(p, False)
            sources_list.append({"name": p, "enabled": is_enabled})
        # Add disabled providers to sources
        for provider_key, is_enabled in provider_states.items():
            if not is_enabled and provider_key not in cached_providers:
                sources_list.append({"name": provider_key, "enabled": False, "message": "disabled_by_admin"})

        response_body = search_schema.SearchResponse(
            items=cached_db.results_json or [],
            total=cached_db.total or 0,
            page=page,
            page_size=page_size,
            sources=sources_list,
            quota=quota_info,
        )
        _search_cache[cache_key] = (time.time(), response_body)
        return response_body

    items = []
    total = 0
    sources = []
    start_ts = time.time()
    status = "ok"
    error_code = None
    skipped_providers = []
    pending_job_id = None
    pending_message = None

    # Internal-first search logic
    internal_provider = None
    external_providers = []

    for provider in providers:
        if provider.name == "internal_catalog":
            internal_provider = provider
        else:
            external_providers.append(provider)

    try:
        # STEP 1: Query internal catalog first if internal-first mode is enabled
        if settings.search_internal_first and internal_provider:
            should_execute, skip_reason = _should_execute_provider(internal_provider, filters)

            if should_execute:
                provider_items, provider_total, meta = internal_provider.search_listings(
                    query=q,
                    filters=filters,
                    page=page,
                    page_size=page_size,
                )
                items.extend(provider_items)
                total += provider_total
                sources.append(meta)
                logging.getLogger(__name__).info(
                    f"Internal catalog returned {provider_total} results"
                )
            else:
                sources.append({
                    "name": internal_provider.name,
                    "enabled": True,
                    "skipped": True,
                    "skip_reason": skip_reason,
                })
                skipped_providers.append({"name": internal_provider.name, "reason": skip_reason})

        # STEP 2: Query external providers only if:
        # - Internal-first is disabled, OR
        # - Internal results < threshold AND external fallback is enabled
        should_query_external = (
            not settings.search_internal_first or
            (total < settings.search_internal_min_results and settings.search_external_fallback_enabled)
        )

        if should_query_external:
            # If using fallback, log it
            if settings.search_internal_first and total < settings.search_internal_min_results:
                logging.getLogger(__name__).info(
                    f"Internal results ({total}) below threshold ({settings.search_internal_min_results}), "
                    f"querying external providers (fallback enabled: {settings.search_external_fallback_enabled})"
                )

            for provider in external_providers:
                should_execute, skip_reason = _should_execute_provider(provider, filters)

                if not should_execute:
                    sources.append({
                        "name": provider.name,
                        "enabled": True,
                        "skipped": True,
                        "skip_reason": skip_reason,
                    })
                    skipped_providers.append({"name": provider.name, "reason": skip_reason})
                    logging.getLogger(__name__).info(
                        f"Skipped provider {provider.name}: {skip_reason}"
                    )
                    continue

                provider_items, provider_total, meta = provider.search_listings(
                    query=q,
                    filters=filters,
                    page=page,
                    page_size=page_size,
                )
                items.extend(provider_items)
                total += provider_total
                sources.append(meta)
        else:
            # Mark external providers as skipped (not queried due to internal-first logic)
            for provider in external_providers:
                sources.append({
                    "name": provider.name,
                    "enabled": True,
                    "skipped": True,
                    "skip_reason": "internal_first_sufficient",
                })
                skipped_providers.append({"name": provider.name, "reason": "internal_first_sufficient"})
            logging.getLogger(__name__).info(
                f"Skipping external providers - internal catalog returned sufficient results ({total})"
            )

    except Exception:
        status = "error"
        error_code = "provider_error"
        response.headers["X-Cache"] = "MISS"
        try:
            search_service.log_search_event(
                db,
                user_id=user_id,
                session_id=session_id,
                query_raw=query_raw,
                query_normalized=query_normalized,
                filters=filters,
                providers=[p.name for p in providers],
                result_count=0,
                latency_ms=None,
                cache_hit=False,
                rate_limited=False,
                status=status,
                error_code=error_code,
            )
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="Search unavailable")

    latency_ms = int((time.time() - start_ts) * 1000)

    crawl_enabled = bool(crawl_allowlist)
    should_enqueue_crawl = crawl_enabled and (deep or total < crawl_min_results)

    if should_enqueue_crawl:
        try:
            job = search_job_service.create_job(
                db,
                user_id=user_id,
                query_normalized=query_normalized,
                filters=filters,
            )
            pending_job_id = job.id
            pending_message = "async_crawl_pending"
            existing_source_names = {s.get("name") for s in sources}
            if "web_crawl_on_demand" not in existing_source_names:
                sources.append({"name": "web_crawl_on_demand", "enabled": True, "message": "queued"})
            try:
                run_on_demand_crawl.delay(job.id)
            except Exception:
                # Fallback to inline execution if Celery broker is unavailable.
                run_on_demand_crawl(job.id)
        except Exception as exc:
            logging.getLogger(__name__).warning("enqueue crawl failed: %s", exc)
            pending_message = "crawl_unavailable"
    quota_info = None
    try:
        usage = None
        should_increment = total > 0
        if current_user:
            if should_increment:
                usage = usage_service.increment_search_usage(db, current_user.id)
            else:
                usage = usage_service.get_or_create_today_usage(db, current_user.id)
            remaining = None
            if plan_limit is not None:
                remaining = max(plan_limit - usage.search_count, 0)
            quota_info = search_schema.SearchQuota(
                limit=plan_limit,
                used=usage.search_count,
                remaining=remaining,
                reset_at=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                if plan_limit is not None
                else None,
            )
        search_service.log_search_event(
            db,
            user_id=user_id,
            session_id=session_id,
            query_raw=query_raw,
            query_normalized=query_normalized,
            filters=filters,
            providers=[p.name for p in providers],
            result_count=total,
            latency_ms=latency_ms,
            cache_hit=False,
            rate_limited=False,
            status=status,
            error_code=error_code,
        )
    except Exception:
        pass

    if not pending_job_id and not deep:
        try:
            search_cache_service.set_cached(
                db,
                signature=signature,
                providers=[p.name for p in providers],
                query_normalized=query_normalized,
                filters=filters,
                page=page,
                limit=page_size,
                total=total,
                results=items,
            )
        except Exception as exc:
            db.rollback()
            logging.getLogger(__name__).warning("search cache set failed: %s", exc)

    # Add disabled providers to sources list
    executed_provider_names = {s.get("name") for s in sources}
    for provider_key, is_enabled in provider_states.items():
        if not is_enabled and provider_key not in executed_provider_names:
            sources.append({"name": provider_key, "enabled": False, "message": "disabled_by_admin"})

    response_body = search_schema.SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        sources=sources,
        quota=quota_info,
        status="pending" if pending_job_id else status,
        job_id=pending_job_id,
        message=pending_message,
    )

    response.headers["X-Cache"] = "MISS"

    if not pending_job_id and not deep:
        _search_cache[cache_key] = (now, response_body)

    return response_body


@router.get("/search/jobs/{job_id}", response_model=search_schema.SearchJobResponse)
def get_search_job(job_id: int, db: Session = Depends(get_db)):
    job, results = search_job_service.get_job_with_results(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return search_schema.SearchJobResponse(
        job_id=job.id,
        status=job.status,
        result_count=job.result_count,
        error=job.error,
        results=[
            search_schema.SearchJobResult(
                title=r.title,
                year=r.year,
                make=r.make,
                model=r.model,
                price=r.price,
                location=r.location,
                source_domain=r.source_domain,
                url=r.url,
                fetched_at=r.fetched_at,
            )
            for r in results
        ],
    )



@router.get("/search/fields")
def get_search_fields(db: Session = Depends(get_db)):
    """
    Get all enabled search fields for public use.
    
    Returns fields ordered by ID, including ui_widget and type info for building search forms.
    """
    fields = (
        db.query(SearchField)
        .filter(SearchField.enabled == True)
        .order_by(SearchField.id)
        .all()
    )
    
    return [
        {
            "key": field.key,
            "label": field.label,
            "data_type": field.data_type,
            "filterable": field.filterable,
            "sortable": field.sortable,
            "visible_in_search": field.visible_in_search,
            "visible_in_results": field.visible_in_results,
            "ui_widget": field.ui_widget,
        }
        for field in fields
    ]
