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
    proxy_id: Optional[int] = None
    proxy_exit_ip: Optional[str] = None
    proxy_error: Optional[str] = None
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
    proxy_id: Optional[int] = Field(None, description="Optional proxy from proxy pool")
    fetch_mode: str = Field(default="http", description="Fetch mode: 'http' or 'browser'")


class BidfaxTestParseRequest(BaseModel):
    """Schema for test-parse endpoint."""
    url: str = Field(..., description="Bidfax URL to test parse")
    proxy_id: Optional[int] = Field(None, description="Optional proxy from proxy pool")
    fetch_mode: str = Field(default="http", description="Fetch mode: 'http' or 'browser'")


class TrackingRetryRequest(BaseModel):
    """Schema for retrying a failed tracking."""
    reset_attempts: bool = Field(default=False, description="Reset attempt counter to 0")


# ============================================================================
# Test Parse Response Schemas
# ============================================================================

class HttpInfo(BaseModel):
    """HTTP request diagnostics."""
    status: int
    error: Optional[str] = None
    latency_ms: int


class ErrorInfo(BaseModel):
    """Top-level error descriptor with stage + code."""
    code: Optional[str] = None
    stage: Optional[str] = None
    message: Optional[str] = None


class ProxyInfo(BaseModel):
    """Proxy diagnostics."""
    used: bool
    proxy_id: Optional[int] = None
    proxy_name: Optional[str] = None
    exit_ip: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    stage: Optional[str] = None
    latency_ms: Optional[int] = None


class ParseInfo(BaseModel):
    """Parsing results and validation."""
    ok: bool
    missing: list[str] = Field(default_factory=list)
    sale_status: Optional[str] = None
    final_bid: Optional[int] = None  # In cents
    vin: Optional[str] = None
    lot_id: Optional[str] = None
    sold_at: Optional[str] = None


class DebugInfo(BaseModel):
    """Debug metadata."""
    url: str
    provider: str = "bidfax_html"
    fetch_mode: str = "http"
    request_id: Optional[str] = None
    attempts: list[dict] = Field(default_factory=list)


class BidfaxTestParseResponse(BaseModel):
    """Structured response for test-parse endpoint."""
    ok: bool
    http: HttpInfo
    proxy: ProxyInfo
    parse: ParseInfo
    debug: DebugInfo
    fetch_mode: str = "http"
    final_url: Optional[str] = None
    html: Optional[str] = None
    error: Optional[ErrorInfo] = None
