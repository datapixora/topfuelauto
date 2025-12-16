from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class MergedListingAttribute(Base):
    """Key-value attributes for merged listings (variable fields)."""
    __tablename__ = "merged_listing_attributes"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("merged_listings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Attribute key-value
    key = Column(Text, nullable=False)
    value_text = Column(Text, nullable=True)
    value_num = Column(Numeric(20, 4), nullable=True)
    value_bool = Column(Boolean, nullable=True)
    unit = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    listing = relationship("MergedListing", back_populates="attributes")

    __table_args__ = (
        Index("ix_merged_attributes_listing_key", "listing_id", "key"),
    )
