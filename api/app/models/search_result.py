from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class SearchResult(Base):
    __tablename__ = "search_results"
    __table_args__ = (Index("ix_search_results_job_id", "job_id"),)

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("search_jobs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    year = Column(Integer, nullable=True)
    make = Column(String(80), nullable=True)
    model = Column(String(80), nullable=True)
    price = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)
    source_domain = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    extra_json = Column(JSONB, nullable=True)

