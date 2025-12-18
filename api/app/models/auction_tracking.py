"""Auction Tracking model for managing crawler task state."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AuctionTracking(Base):
    """
    Crawler task tracking table for auction data sources.

    Manages crawl state, retry logic, and scheduling for each target URL.
    Supports exponential backoff and Celery Beat integration.
    """
    __tablename__ = "auction_tracking"

    id = Column(Integer, primary_key=True, index=True)

    # Target configuration
    target_url = Column(Text, nullable=False)  # Full URL to crawl
    target_type = Column(String(20), nullable=False)  # list_page / detail_page

    # Metadata for grouping and filtering
    make = Column(String(100), nullable=True, index=True)  # Vehicle make (e.g., "Ford")
    model = Column(String(100), nullable=True, index=True)  # Vehicle model (e.g., "C-Max")
    page_num = Column(Integer, nullable=True)  # Page number in pagination sequence

    # Scheduling
    next_check_at = Column(DateTime, nullable=True, index=True)  # When to next crawl this URL

    # Retry logic
    attempts = Column(Integer, nullable=False, default=0)  # Number of fetch attempts

    # Status tracking
    status = Column(String(20), nullable=False, default="pending", index=True)
    # Possible statuses: pending, running, done, failed

    last_error = Column(Text, nullable=True)  # Last error message (if failed)
    last_http_status = Column(Integer, nullable=True)  # Last HTTP status code
    last_seen_at = Column(DateTime, nullable=True)  # Last time URL was processed

    # Statistics (stored as JSONB for flexibility)
    stats = Column(JSONB, nullable=False, default=dict)
    # Example: {items_found: 10, items_saved: 8, new_records: 3, updated_records: 5}

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Prevent duplicate tracking for same URL
        UniqueConstraint("target_url", name="uq_auction_tracking_target_url"),

        # Composite index for beat scheduler queries
        Index("ix_auction_tracking_status_next_check", "status", "next_check_at"),
    )

    def __repr__(self):
        return f"<AuctionTracking(id={self.id}, url={self.target_url[:50]}..., status={self.status}, attempts={self.attempts})>"
