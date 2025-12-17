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


class DataListingStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    UNKNOWN = "unknown"


class DataListing(Base):
    __tablename__ = "data_listings"

    id = Column(Integer, primary_key=True, index=True)
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
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    merged_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(SAEnum(DataListingStatus), default=DataListingStatus.UNKNOWN, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    attributes = relationship("DataListingAttribute", back_populates="listing")

    __table_args__ = (UniqueConstraint("source_key", "canonical_url", name="_data_source_canonical_uc"),)


class DataListingAttribute(Base):
    __tablename__ = "data_listing_attributes"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("data_listings.id"), nullable=False)
    key = Column(Text, nullable=False)
    value_text = Column(Text, nullable=True)
    value_num = Column(Numeric, nullable=True)
    value_bool = Column(Boolean, nullable=True)
    unit = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    listing = relationship("DataListing", back_populates="attributes")
