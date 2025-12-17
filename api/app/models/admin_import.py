from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, LargeBinary, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AdminImport(Base):
    """CSV import tracking and management."""
    __tablename__ = "admin_imports"

    id = Column(Integer, primary_key=True, index=True)

    # File metadata
    source_key = Column(String(100), nullable=True, index=True)  # Optional source identifier
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)  # For deduplication
    file_data = Column(LargeBinary, nullable=True)  # Store file bytes

    # Status: UPLOADED, PARSING, READY, RUNNING, SUCCEEDED, FAILED, CANCELLED
    status = Column(String(20), nullable=False, default="UPLOADED", index=True)

    # Progress tracking
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, nullable=False, default=0)
    created_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)

    # CSV structure and mapping
    detected_headers = Column(JSONB, nullable=True)  # ["Lot URL", "Year", "Make", ...]
    column_map = Column(JSONB, nullable=True)  # {"Lot URL": "url", "Year": "year", ...}
    sample_preview = Column(JSONB, nullable=True)  # First 20 rows as array of objects

    # Error tracking
    error_log = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_admin_imports_created_at", "created_at"),
        Index("ix_admin_imports_source_key", "source_key"),
    )
