"""Auction Sale model for storing sold results from auction sites."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AuctionSale(Base):
    """
    Truth table for auction sold results (Bidfax, etc.).

    Stores verified sold prices and vehicle attributes from auction sites.
    Used for pricing intelligence, expected sold price models, and deal scoring.
    """
    __tablename__ = "auction_sales"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Core identifiers (at least one required)
    vin = Column(String(17), nullable=True, index=True)  # Normalized uppercase, 17-char VIN
    lot_id = Column(String(100), nullable=True, index=True)  # Auction lot number

    # Auction metadata
    auction_source = Column(String(50), nullable=False, index=True)  # copart/iaai/unknown
    sale_status = Column(String(50), nullable=False)  # sold/on_approval/no_sale/unknown

    # Financial data
    sold_price = Column(Integer, nullable=True)  # Price in cents (USD)
    currency = Column(String(10), nullable=False, default="USD")

    # Sale timing
    sold_at = Column(DateTime, nullable=True, index=True)  # Date of sale

    # Vehicle attributes
    location = Column(String(255), nullable=True)  # Sale location (e.g., "CA - Los Angeles")
    odometer_miles = Column(Integer, nullable=True)  # Mileage in miles
    damage = Column(String(255), nullable=True)  # Primary damage type
    condition = Column(String(100), nullable=True)  # Condition (e.g., "Run and Drive")

    # Dynamic storage for extra fields
    attributes = Column(JSONB, nullable=False, default=dict)  # Additional extracted fields
    raw_payload = Column(JSONB, nullable=True)  # Full raw data from scraper for debugging

    # Source tracking
    source_url = Column(Text, nullable=False)  # List or detail page URL where data was extracted

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Composite unique constraint for deduplication
        # Allows UPSERT on same VIN/source/lot combination
        UniqueConstraint("vin", "auction_source", "lot_id", name="uq_auction_sale_vin_source_lot"),

        # Composite index for common queries
        Index("ix_auction_sales_vin_source", "vin", "auction_source"),
        Index("ix_auction_sales_sold_at", "sold_at"),
    )

    def __repr__(self):
        return f"<AuctionSale(id={self.id}, vin={self.vin}, lot={self.lot_id}, source={self.auction_source}, price={self.sold_price})>"
