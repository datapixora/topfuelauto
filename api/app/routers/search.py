import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_optional_user
from app.providers import get_active_providers
from app.schemas import search as search_schema
from app.services import search_service

router = APIRouter(prefix="/api/v1", tags=["search"])

CACHE_TTL_SECONDS = 45
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60

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
    # prune
    _rate_limit[ip] = [t for t in events if t >= window_start]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    _rate_limit[ip].append(now)


@router.get("/search", response_model=search_schema.SearchResponse)
def search(
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
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

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
        return cached[1]

    settings = get_settings()
    providers = get_active_providers(settings)

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

    items = []
    total = 0
    sources = []

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

    response = search_schema.SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        sources=sources,
    )

    _search_cache[cache_key] = (now, response)

    try:
        search_service.log_search_event(
            db,
            query=q,
            filters={**filters, "providers": [p.name for p in providers]},
            user_id=getattr(current_user, "id", None) if current_user else None,
            results_count=total,
            latency_ms=None,
        )
    except Exception:
        pass

    return response
