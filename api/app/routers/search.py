from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import search_service
from app.schemas import search as search_schema

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search", response_model=list[search_schema.SearchResult])
def search(
    q: str = Query(..., min_length=1),
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    location: str | None = None,
    condition: str | None = None,
    transmission: str | None = None,
    sort: str | None = None,
    db: Session = Depends(get_db),
):
    rows = search_service.search_listings(
        db,
        q=q,
        year_min=year_min,
        year_max=year_max,
        price_min=price_min,
        price_max=price_max,
        location=location,
        condition=condition,
        transmission=transmission,
        sort=sort,
    )
    results = [
        search_schema.SearchResult(
            listing_id=row.listing_id,
            title=row.title,
            year=row.year,
            make=row.make,
            model=row.model,
            trim=row.trim,
            price=row.price,
            currency=row.currency,
            location=row.location,
            end_date=row.end_date,
            risk_flags=row.risk_flags,
            score=row.score,
        )
        for row in rows
    ]
    return results