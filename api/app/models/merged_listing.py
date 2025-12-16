from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class MergedListing(Base):
    """Main merged listings table (approved from staging)."""
    __tablename__ = "merged_listings"

    id = Column(Integer, primary_key=True, index=True)

    # Source identification
    source_key = Column(String(100), nullable=False, index=True)
    source_listing_id = Column(String(255), nullable=True)
    canonical_url = Column(Text, nullable=False)

    # Base fields (minimal)
    title = Column(Text, nullable=True)
    year = Column(Integer, nullable=True, index=True)
    make = Column(String(100), nullable=True, index=True)
    model = Column(String(100), nullable=True, index=True)

    # Price
    price_amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), nullable=True, default="USD")

    # Location and metadata
    odometer_value = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)
    listed_at = Column(DateTime, nullable=True)
    sale_datetime = Column(DateTime, nullable=True)

    # Fetch metadata
    fetched_at = Column(DateTime, nullable=False)

    # Status: active, ended, unknown
    status = Column(String(20), nullable=False, default="unknown")

    # Merge metadata
    merged_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attributes = relationship("MergedListingAttribute", back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_key", "canonical_url", name="uq_merged_listing_source_url"),
        Index("ix_merged_listings_merged_at", "merged_at"),
    )
