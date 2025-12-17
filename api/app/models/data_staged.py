from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Enum as SAEnum,
    Numeric,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class StagedListingStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    UNKNOWN = "unknown"


class StagedListing(Base):
    __tablename__ = "staged_listings"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("admin_runs.id"), nullable=False)
    source_key = Column(String, nullable=False, index=True)
    source_listing_id = Column(String, nullable=True)
    canonical_url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    make = Column(String, nullable=True)
    model = Column(String, nullable=True)
    price_amount = Column(Numeric, nullable=True)
    currency = Column(String, nullable=True)
    odometer_value = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    listed_at = Column(DateTime(timezone=True), nullable=True)
    sale_datetime = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(SAEnum(StagedListingStatus), default=StagedListingStatus.UNKNOWN, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    run = relationship("AdminRun")
    attributes = relationship("StagedListingAttribute", back_populates="listing")

    __table_args__ = (UniqueConstraint("source_key", "canonical_url", name="_source_canonical_uc"),)


class StagedListingAttribute(Base):
    __tablename__ = "staged_listing_attributes"

    id = Column(Integer, primary_key=True, index=True)
    staged_listing_id = Column(Integer, ForeignKey("staged_listings.id"), nullable=False)
    key = Column(Text, nullable=False)
    value_text = Column(Text, nullable=True)
    value_num = Column(Numeric, nullable=True)
    value_bool = Column(Boolean, nullable=True)
    unit = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    listing = relationship("StagedListing", back_populates="attributes")
