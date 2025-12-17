"""Schemas for CSV import system."""

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class ImportUploadResponse(BaseModel):
    """Response after uploading a CSV file."""
    import_id: int
    filename: str
    file_size: int
    sha256: str
    total_rows: int
    detected_headers: List[str]
    sample_preview: List[Dict[str, Any]]  # First 20 rows
    suggested_mapping: Dict[str, str]  # CSV column -> target field mapping
    status: str


class ImportStartRequest(BaseModel):
    """Request to start processing an import."""
    column_map: Dict[str, str] = Field(..., description="CSV column name -> target field mapping")
    source_key: Optional[str] = Field(None, description="Optional source identifier (e.g., 'copart_manual')")
    skip_duplicates: bool = Field(True, description="Skip rows that already exist (by URL)")


class ImportProgressResponse(BaseModel):
    """Import progress and status."""
    id: int
    filename: str
    status: str
    total_rows: Optional[int]
    processed_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    error_log: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class ImportSummary(BaseModel):
    """Brief import summary for list view."""
    id: int
    filename: str
    status: str
    total_rows: Optional[int]
    processed_rows: int
    created_count: int
    error_count: int
    created_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True
