from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class SearchCacheEntry(Base):
    __tablename__ = "search_cache_entries"
    __table_args__ = (UniqueConstraint("signature", name="uq_search_cache_signature"),)

    id = Column(Integer, primary_key=True)
    signature = Column(String(255), nullable=False, unique=True)
    providers_json = Column(JSONB, nullable=True)
    query_normalized = Column(String(255), nullable=True)
    filters_json = Column(JSONB, nullable=True)
    page = Column(Integer, nullable=True)
    limit = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    results_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
