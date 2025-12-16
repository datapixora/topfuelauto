from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AdminSource(Base):
    """Admin-controlled data source for scraping/importing."""
    __tablename__ = "admin_sources"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    base_url = Column(Text, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)

    # Mode: "list_only" = scrape list page only, "follow_details" = crawl detail links with caps
    mode = Column(String(20), nullable=False, default="list_only")

    # Schedule and limits
    schedule_minutes = Column(Integer, nullable=False, default=60)
    max_items_per_run = Column(Integer, nullable=False, default=20)
    max_pages_per_run = Column(Integer, nullable=False, default=5)

    # Rate limiting
    rate_per_minute = Column(Integer, nullable=False, default=30)
    concurrency = Column(Integer, nullable=False, default=2)
    timeout_seconds = Column(Integer, nullable=False, default=10)
    retry_count = Column(Integer, nullable=False, default=1)

    # Configuration (selectors, recipes, allowlist paths)
    settings_json = Column(JSONB, nullable=True)
    merge_rules = Column(JSONB, nullable=True)
    last_block_reason = Column(Text, nullable=True)
    last_blocked_at = Column(DateTime, nullable=True)
    cooldown_until = Column(DateTime, nullable=True)

    # Failure tracking
    failure_count = Column(Integer, nullable=False, default=0)
    disabled_reason = Column(Text, nullable=True)

    # Scheduling
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_admin_sources_enabled_next_run", "is_enabled", "next_run_at"),
    )
