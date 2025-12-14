import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_optional_user
from app.providers import get_active_providers
from app.schemas import search as search_schema
from app.services import search_service
from app.services import usage_service
from app.models.plan import Plan

router = APIRouter(prefix="/api/v1", tags=["search"])

CACHE_TTL_SECONDS = 45
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60
DEFAULT_FREE_SEARCHES_PER_DAY = 5

_search_cache: Dict[str, Tuple[float, search_schema.SearchResponse]] = {}
_rate_limit: Dict[str, list[float]] = defaultdict(list)


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
    query_normalized = " ".join(q.strip().lower().split())

    filters = {
        "make": make,
        "model": model,
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
    if current_user:
        plan_key = "pro" if getattr(current_user, "is_pro", False) else "free"
        plan = db.query(Plan).filter(Plan.key == plan_key, Plan.is_active.is_(True)).first()
        if plan and plan.searches_per_day is not None:
            plan_limit = plan.searches_per_day
        elif plan_key == "free":
            plan_limit = DEFAULT_FREE_SEARCHES_PER_DAY  # fail-safe default for free if plan config missing
        if plan and plan.quota_reached_message:
            quota_message = plan.quota_reached_message

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

    cache_key = _make_cache_key(
        client_ip,
        q,
        make,
        model,
        year_min,
        year_max,
        price_min,
        price_max,
        location,
        sort,
        page,
        page_size,
    )
    cached = _search_cache.get(cache_key)
    now = time.time()
    if cached and now - cached[0] <= CACHE_TTL_SECONDS:
        response.headers["X-Cache"] = "HIT"
        quota_info = None
        try:
            usage = None
            should_increment = cached[1].total > 0 if cached[1] else False
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

    settings = get_settings()
    providers = get_active_providers(settings)

    items = []
    total = 0
    sources = []
    start_ts = time.time()
    status = "ok"
    error_code = None

    try:
        for provider in providers:
            provider_items, provider_total, meta = provider.search_listings(
                query=q,
                filters=filters,
                page=page,
                page_size=page_size,
            )
            items.extend(provider_items)
            total += provider_total
            sources.append(meta)
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

    response_body = search_schema.SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        sources=sources,
        quota=quota_info,
    )

    response.headers["X-Cache"] = "MISS"

    _search_cache[cache_key] = (now, response_body)

    return response_body
