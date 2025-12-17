"""Internal catalog provider - queries merged_listings table."""

import logging
from typing import Any, Dict, List, Tuple
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from app.models.merged_listing import MergedListing
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class InternalCatalogProvider:
    """Provider that searches imported listings from merged_listings table."""

    name = "internal_catalog"
    requires_structured = False  # Can work with free-text or structured
    supports_free_text = True  # Handles free-form queries

    def __init__(self):
        self.enabled = True

    def normalize_listing(self, listing: MergedListing) -> Dict[str, Any]:
        """Convert MergedListing to standard search result format."""
        return {
            "id": f"{self.name}:{listing.id}",
            "listing_id": f"{self.name}:{listing.id}",
            "title": listing.title or f"{listing.year or ''} {listing.make or ''} {listing.model or ''}".strip() or "Imported Listing",
            "year": listing.year,
            "make": listing.make,
            "model": listing.model,
            "price": float(listing.price_amount) if listing.price_amount else None,
            "currency": listing.currency or "USD",
            "location": listing.location,
            "url": listing.canonical_url,
            "source": self.name,
            "risk_flags": [],
            "mileage": listing.odometer_value,
            "sale_date": listing.sale_datetime.isoformat() if listing.sale_datetime else None,
            "source_key": listing.source_key,
        }

    def search_listings(
        self,
        query: str,
        filters: Dict[str, Any],
        page: int,
        page_size: int,
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        Search merged_listings table with filters.

        Args:
            query: Free-text search query
            filters: Dict with make, model, year_min, year_max, price_min, price_max, location
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            (listings, total_count, provider_metadata)
        """
        db: Session = SessionLocal()

        try:
            # Build query
            query_obj = db.query(MergedListing).filter(MergedListing.status == "active")

            # Apply filters
            conditions = []

            # Make filter
            if filters.get("make"):
                make_filter = filters["make"].upper()
                conditions.append(MergedListing.make == make_filter)

            # Model filter
            if filters.get("model"):
                model_filter = filters["model"]
                conditions.append(func.lower(MergedListing.model).like(f"%{model_filter.lower()}%"))

            # Year range
            if filters.get("year_min"):
                conditions.append(MergedListing.year >= filters["year_min"])
            if filters.get("year_max"):
                conditions.append(MergedListing.year <= filters["year_max"])

            # Price range
            if filters.get("price_min"):
                conditions.append(MergedListing.price_amount >= filters["price_min"])
            if filters.get("price_max"):
                conditions.append(MergedListing.price_amount <= filters["price_max"])

            # Location filter
            if filters.get("location"):
                location_filter = filters["location"]
                conditions.append(func.lower(MergedListing.location).like(f"%{location_filter.lower()}%"))

            # Free-text search (title or make/model)
            if query and query.strip():
                query_lower = query.lower()
                text_conditions = []

                # Search in title
                text_conditions.append(func.lower(MergedListing.title).like(f"%{query_lower}%"))

                # Search in make/model
                text_conditions.append(func.lower(MergedListing.make).like(f"%{query_lower}%"))
                text_conditions.append(func.lower(MergedListing.model).like(f"%{query_lower}%"))

                conditions.append(or_(*text_conditions))

            if conditions:
                query_obj = query_obj.filter(and_(*conditions))

            # Get total count
            total_count = query_obj.count()

            # Apply sorting
            sort = filters.get("sort", "newest")
            if sort == "newest":
                query_obj = query_obj.order_by(MergedListing.created_at.desc())
            elif sort == "price_low":
                query_obj = query_obj.order_by(MergedListing.price_amount.asc().nullslast())
            elif sort == "price_high":
                query_obj = query_obj.order_by(MergedListing.price_amount.desc().nullslast())
            elif sort == "year_new":
                query_obj = query_obj.order_by(MergedListing.year.desc().nullslast())
            elif sort == "year_old":
                query_obj = query_obj.order_by(MergedListing.year.asc().nullslast())
            else:
                # Default: newest first
                query_obj = query_obj.order_by(MergedListing.created_at.desc())

            # Apply pagination
            offset = (page - 1) * page_size
            results = query_obj.limit(page_size).offset(offset).all()

            # Normalize results
            listings = [self.normalize_listing(listing) for listing in results]

            logger.info(f"InternalCatalogProvider: {len(listings)} results (total: {total_count})")

            return listings, total_count, {
                "name": self.name,
                "enabled": True,
                "query_count": len(listings),
                "total_count": total_count,
            }

        except Exception as e:
            logger.error(f"InternalCatalogProvider search error: {type(e).__name__}: {e}", exc_info=True)
            return [], 0, {
                "name": self.name,
                "enabled": True,
                "error": f"{type(e).__name__}: {str(e)}",
            }

        finally:
            db.close()
