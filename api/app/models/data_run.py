from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Enum as SAEnum,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class RunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PAUSED = "paused"


class AdminRun(Base):
    __tablename__ = "admin_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("admin_sources.id"), nullable=False)
    status = Column(SAEnum(RunStatus), default=RunStatus.QUEUED, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    pages_planned = Column(Integer, nullable=True)
    pages_done = Column(Integer, default=0)
    items_found = Column(Integer, default=0)
    items_staged = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)
    debug_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source = relationship("AdminSource")
