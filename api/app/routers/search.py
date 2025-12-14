from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_optional_user
from app.providers import get_active_providers
from app.schemas import search as search_schema
from app.services import search_service

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search", response_model=search_schema.SearchResponse)
def search(
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

    # log search event (provider names only)
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

    return search_schema.SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        sources=sources,
    )
