from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey, UniqueConstraint, Index, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class StagedListing(Base):
    """Staging area for scraped listings before merge to main."""
    __tablename__ = "staged_listings"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("admin_runs.id", ondelete="CASCADE"), nullable=False, index=True)

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
    confidence_score = Column(Numeric(5, 3), nullable=True)

    # Location and metadata
    odometer_value = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)
    listed_at = Column(DateTime, nullable=True)
    sale_datetime = Column(DateTime, nullable=True)

    # Fetch metadata
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Status: active, ended, unknown
    status = Column(String(20), nullable=False, default="unknown")
    auto_approved = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    run = relationship("AdminRun", backref="staged_items")
    attributes = relationship("StagedListingAttribute", back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_key", "canonical_url", name="uq_staged_listing_source_url"),
        Index("ix_staged_listings_run_created", "run_id", "created_at"),
    )
