from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class AdminRun(Base):
    """Execution run for an admin source."""
    __tablename__ = "admin_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("admin_sources.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status: queued, running, succeeded, failed, paused
    status = Column(String(20), nullable=False, default="queued", index=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Progress tracking
    pages_planned = Column(Integer, nullable=False, default=1)  # Never 0 to avoid division errors
    pages_done = Column(Integer, nullable=False, default=0)
    items_found = Column(Integer, nullable=False, default=0)
    items_staged = Column(Integer, nullable=False, default=0)

    # Error tracking
    error_summary = Column(Text, nullable=True)
    debug_json = Column(JSONB, nullable=True)

    # Proxy info
    proxy_id = Column(Integer, ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True, index=True)
    proxy_exit_ip = Column(String(64), nullable=True)
    proxy_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationship
    source = relationship("AdminSource", backref="runs")

    __table_args__ = (
        Index("ix_admin_runs_source_created", "source_id", "created_at"),
    )
