"""Pydantic schemas for auction sales and tracking endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# ============================================================================
# Auction Sales Schemas
# ============================================================================

class AuctionSaleBase(BaseModel):
    """Base schema for AuctionSale."""
    vin: Optional[str] = None
    lot_id: Optional[str] = None
    auction_source: str
    sale_status: str
    sold_price: Optional[int] = None  # Price in cents
    currency: str = "USD"
    sold_at: Optional[datetime] = None
    location: Optional[str] = None
    odometer_miles: Optional[int] = None
    damage: Optional[str] = None
    condition: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    source_url: str


class AuctionSaleCreate(AuctionSaleBase):
    """Schema for creating a new auction sale."""
    raw_payload: Optional[Dict[str, Any]] = None


class AuctionSaleResponse(AuctionSaleBase):
    """Schema for auction sale response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Auction Tracking Schemas
# ============================================================================

class AuctionTrackingBase(BaseModel):
    """Base schema for AuctionTracking."""
    target_url: str
    target_type: str = "list_page"
    make: Optional[str] = None
    model: Optional[str] = None
    page_num: Optional[int] = None


class AuctionTrackingCreate(AuctionTrackingBase):
    """Schema for creating a new tracking row."""
    pass


class AuctionTrackingUpdate(BaseModel):
    """Schema for updating tracking row (all fields optional)."""
    status: Optional[str] = None
    last_error: Optional[str] = None
    last_http_status: Optional[int] = None
    stats: Optional[Dict[str, Any]] = None
    attempts: Optional[int] = None
    next_check_at: Optional[datetime] = None


class AuctionTrackingResponse(AuctionTrackingBase):
    """Schema for auction tracking response."""
    id: int
    status: str
    attempts: int
    last_error: Optional[str]
    last_http_status: Optional[int]
    stats: Dict[str, Any]
    next_check_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# API Request Schemas
# ============================================================================

class BidfaxJobCreate(BaseModel):
    """Schema for creating a Bidfax crawl job."""
    target_url: str = Field(..., description="Bidfax list page URL (e.g., https://en.bidfax.info/ford/c-max/)")
    pages: int = Field(default=1, ge=1, le=100, description="Number of pages to crawl (1-100)")
    make: Optional[str] = Field(None, description="Vehicle make for metadata (optional)")
    model: Optional[str] = Field(None, description="Vehicle model for metadata (optional)")
    schedule_enabled: bool = Field(default=False, description="Enable recurring scheduled crawls")
    schedule_interval_minutes: Optional[int] = Field(default=60, ge=10, description="Interval between scheduled crawls (min 10)")


class TrackingRetryRequest(BaseModel):
    """Schema for retrying a failed tracking."""
    reset_attempts: bool = Field(default=False, description="Reset attempt counter to 0")
