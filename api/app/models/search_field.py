"""SearchField model for dynamic field registry."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class SearchField(Base):
    """
    Dynamic field registry for search and import mapping.

    Allows adding new searchable fields without DB migrations.
    Fields can be stored in core columns (storage='core') or JSONB extra (storage='extra').
    """
    __tablename__ = "search_fields"

    id = Column(Integer, primary_key=True, index=True)

    # Field identification
    key = Column(String(100), nullable=False, unique=True, index=True)
    label = Column(String(255), nullable=False)

    # Field configuration
    data_type = Column(String(50), nullable=False)  # integer, string, decimal, boolean, date
    storage = Column(String(20), nullable=False)  # 'core' or 'extra'

    # Feature flags
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    filterable = Column(Boolean, nullable=False, default=True)
    sortable = Column(Boolean, nullable=False, default=False)
    visible_in_search = Column(Boolean, nullable=False, default=True)
    visible_in_results = Column(Boolean, nullable=False, default=True)

    # UI configuration
    ui_widget = Column(String(50), nullable=True)  # text, select, range, date_picker, etc.

    # Import mapping
    source_aliases = Column(JSONB, nullable=False, default=list)  # List of CSV header aliases
    normalization = Column(JSONB, nullable=False, default=dict)  # Transform rules

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
