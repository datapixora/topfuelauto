from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class StagedListingAttribute(Base):
    """Key-value attributes for staged listings (variable fields)."""
    __tablename__ = "staged_listing_attributes"

    id = Column(Integer, primary_key=True, index=True)
    staged_listing_id = Column(Integer, ForeignKey("staged_listings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Attribute key-value
    key = Column(Text, nullable=False)
    value_text = Column(Text, nullable=True)
    value_num = Column(Numeric(20, 4), nullable=True)
    value_bool = Column(Boolean, nullable=True)
    unit = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    listing = relationship("StagedListing", back_populates="attributes", passive_deletes=True)

    __table_args__ = (
        Index("ix_staged_attributes_listing_key", "staged_listing_id", "key"),
    )
