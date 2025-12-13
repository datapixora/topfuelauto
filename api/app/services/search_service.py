from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.vehicle import Vehicle
from app.models.search_event import SearchEvent


def search_listings(
    db: Session,
    q: str,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    location: str | None = None,
    condition: str | None = None,
    transmission: str | None = None,
    sort: str | None = None,
):
    similarity = func.greatest(
        func.similarity(func.unaccent(Listing.title), func.unaccent(q)),
        func.similarity(func.unaccent(Vehicle.make + ' ' + Vehicle.model), func.unaccent(q)),
    )

    ts_rank = func.ts_rank(Listing.search_tsv, func.plainto_tsquery(q))

    score_expr = func.coalesce(ts_rank, 0) + func.coalesce(similarity, 0)

    if price_min and price_max:
        mid = (price_min + price_max) / 2
        budget_boost = 1 / (1 + func.abs(Listing.price - mid) / mid)
        score_expr = score_expr + func.coalesce(budget_boost, 0)

    query = db.query(
        Listing.id.label("listing_id"),
        Listing.title,
        Vehicle.year,
        Vehicle.make,
        Vehicle.model,
        Vehicle.trim,
        Listing.price,
        Listing.currency,
        Listing.location,
        Listing.end_date,
        Listing.risk_flags,
        score_expr.label("score"),
    ).join(Vehicle, Listing.vehicle_id == Vehicle.id)

    if year_min:
        query = query.filter(Vehicle.year >= year_min)
    if year_max:
        query = query.filter(Vehicle.year <= year_max)
    if price_min:
        query = query.filter(Listing.price >= price_min)
    if price_max:
        query = query.filter(Listing.price <= price_max)
    if location:
        query = query.filter(func.lower(Listing.location).like(f"%{location.lower()}%"))
    if condition:
        query = query.filter(Listing.condition == condition)
    if transmission:
        query = query.filter(Listing.transmission == transmission)

    if sort == "end_date":
        query = query.order_by(Listing.end_date.asc())
    else:
        query = query.order_by(score_expr.desc().nullslast(), Listing.created_at.desc())

    return query.limit(50).all()


def log_search_event(
    db: Session,
    query: str,
    filters: dict | None,
    user_id: int | None,
    results_count: int | None,
    latency_ms: int | None,
):
    event = SearchEvent(
        query=query,
        filters=filters,
        user_id=user_id,
        results_count=results_count,
        latency_ms=latency_ms,
    )
    db.add(event)
    db.commit()
