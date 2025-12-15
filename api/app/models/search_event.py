from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class SearchEvent(Base):
    __tablename__ = "search_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    session_id = Column(String(64), nullable=True, index=True)

    # Note: `query` is NOT NULL in the database (created in migration 0002_admin).
    # Keep it in sync to avoid IntegrityError on insert.
    query = Column(String(255), nullable=False, default="")
    query_raw = Column(String(255), nullable=True)
    query_normalized = Column(String(255), nullable=True, index=True)

    filters_json = Column(JSONB, nullable=True)
    providers = Column(JSONB, nullable=True)

    result_count = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cache_hit = Column(Boolean, default=False, nullable=False)
    rate_limited = Column(Boolean, default=False, nullable=False)
    status = Column(String(16), default="ok", nullable=False)
    error_code = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


Index("ix_search_events_ts_querynorm", SearchEvent.created_at, SearchEvent.query_normalized)
