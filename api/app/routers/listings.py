from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import listing_service
from app.schemas import listing as listing_schema

router = APIRouter(prefix="/api/v1/listings", tags=["listings"])


@router.get("/{listing_id}", response_model=listing_schema.ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = listing_service.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("", response_model=list[listing_schema.ListingListItem])
def list_listings(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    listings = listing_service.list_listings(db, skip, limit)
    return listings