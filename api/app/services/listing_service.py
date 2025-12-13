from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.listing import Listing


def get_listing(db: Session, listing_id: int) -> Listing | None:
    return db.query(Listing).options(joinedload(Listing.vehicle)).filter(Listing.id == listing_id).first()


def list_listings(db: Session, skip: int = 0, limit: int = 20):
    return (
        db.query(Listing)
        .options(joinedload(Listing.vehicle))
        .order_by(Listing.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )