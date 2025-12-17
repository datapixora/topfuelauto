"""Schemas for SearchField CRUD."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import re


class SearchFieldBase(BaseModel):
    """Base schema for SearchField."""
    key: str = Field(..., description="Unique slug-like identifier")
    label: str = Field(..., description="Human-readable label")
    data_type: str = Field(..., description="Data type: integer, string, decimal, boolean, date")
    storage: str = Field(..., description="Storage location: core or extra")
    enabled: bool = Field(default=True)
    filterable: bool = Field(default=True)
    sortable: bool = Field(default=False)
    visible_in_search: bool = Field(default=True)
    visible_in_results: bool = Field(default=True)
    ui_widget: Optional[str] = Field(None, description="UI widget type")
    source_aliases: List[str] = Field(default_factory=list, description="CSV header aliases for import mapping")
    normalization: Dict[str, Any] = Field(default_factory=dict, description="Transformation rules")

    @validator('key')
    def validate_key(cls, v):
        """Ensure key is slug-like (lowercase, alphanumeric, underscores)."""
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('key must be lowercase alphanumeric with underscores (e.g., "fuel_type")')
        return v

    @validator('data_type')
    def validate_data_type(cls, v):
        """Ensure data_type is valid."""
        valid_types = ['integer', 'string', 'decimal', 'boolean', 'date']
        if v not in valid_types:
            raise ValueError(f'data_type must be one of: {", ".join(valid_types)}')
        return v

    @validator('storage')
    def validate_storage(cls, v):
        """Ensure storage is valid."""
        if v not in ['core', 'extra']:
            raise ValueError('storage must be "core" or "extra"')
        return v


class SearchFieldCreate(SearchFieldBase):
    """Schema for creating a new SearchField."""
    pass


class SearchFieldUpdate(BaseModel):
    """Schema for updating a SearchField (all fields optional)."""
    label: Optional[str] = None
    enabled: Optional[bool] = None
    filterable: Optional[bool] = None
    sortable: Optional[bool] = None
    visible_in_search: Optional[bool] = None
    visible_in_results: Optional[bool] = None
    ui_widget: Optional[str] = None
    source_aliases: Optional[List[str]] = None
    normalization: Optional[Dict[str, Any]] = None


class SearchFieldResponse(SearchFieldBase):
    """Schema for SearchField response."""
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
        orm_mode = True
