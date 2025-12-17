from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, validator
from app.models.admin_source import ProxyMode


# ============================================================================
# Proxy Schemas
# ============================================================================

class ProxyPoolSummary(BaseModel):
    enabled_count: int
    weight_sum: int
    last_exit_ip: Optional[str]

    class Config:
        from_attributes = True


class ProxyOption(BaseModel):
    id: int
    name: str
    host: str
    port: int
    scheme: str
    last_check_status: Optional[str]
    last_exit_ip: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# Merge Rules
# ============================================================================

class MergeRules(BaseModel):
    auto_merge_enabled: bool = False
    require_year_make_model: bool = True
    require_price_or_url: bool = True
    min_confidence_score: Optional[float] = None


# ============================================================================
# Admin Source Schemas
# ============================================================================

class AdminSourceBase(BaseModel):
    key: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    base_url: str
    is_enabled: bool = True
    mode: str = Field(default="list_only", pattern="^(list_only|follow_details)$")
    schedule_minutes: int = Field(default=60, ge=15)
    max_items_per_run: int = Field(default=20, ge=1)
    max_pages_per_run: int = Field(default=5, ge=1)
    rate_per_minute: int = Field(default=30, ge=1)
    concurrency: int = Field(default=2, ge=1)
    timeout_seconds: int = Field(default=10, ge=1)
    retry_count: int = Field(default=1, ge=0)
    proxy_mode: ProxyMode = ProxyMode.NONE
    proxy_id: Optional[int] = None
    settings_json: Optional[dict] = None
    merge_rules: Optional[MergeRules] = None

    @validator('proxy_mode', pre=True)
    def normalize_proxy_mode(cls, v):
        """Normalize proxy_mode to uppercase to prevent SQLAlchemy enum decode errors."""
        if isinstance(v, str):
            return v.upper()
        return v


class AdminSourceCreate(AdminSourceBase):
    pass


class AdminSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    base_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    mode: Optional[str] = Field(None, pattern="^(list_only|follow_details)$")
    schedule_minutes: Optional[int] = Field(None, ge=15)
    max_items_per_run: Optional[int] = Field(None, ge=1)
    max_pages_per_run: Optional[int] = Field(None, ge=1)
    rate_per_minute: Optional[int] = Field(None, ge=1)
    concurrency: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(None, ge=1)
    retry_count: Optional[int] = Field(None, ge=0)
    proxy_mode: Optional[ProxyMode] = None
    proxy_id: Optional[int] = None
    settings_json: Optional[dict] = None
    merge_rules: Optional[MergeRules] = None

    @validator('proxy_mode', pre=True)
    def normalize_proxy_mode(cls, v):
        """Normalize proxy_mode to uppercase to prevent SQLAlchemy enum decode errors."""
        if isinstance(v, str):
            return v.upper()
        return v


class AdminSourceOut(AdminSourceBase):
    id: int
    last_block_reason: Optional[str] = None
    last_blocked_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    failure_count: int
    disabled_reason: Optional[str] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    proxy_pool_summary: Optional[ProxyPoolSummary] = None

    class Config:
        from_attributes = True


# ============================================================================
# Admin Run Schemas
# ============================================================================

class AdminRunBase(BaseModel):
    source_id: int
    status: str = Field(default="queued", pattern="^(queued|running|succeeded|failed|paused|blocked|proxy_failed)$")
    proxy_id: Optional[int] = None


class AdminRunCreate(AdminRunBase):
    pass


class AdminRunUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(queued|running|succeeded|failed|paused|blocked|proxy_failed)$")
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    pages_planned: Optional[int] = None
    pages_done: Optional[int] = None
    items_found: Optional[int] = None
    items_staged: Optional[int] = None
    error_summary: Optional[str] = None
    debug_json: Optional[dict] = None
    proxy_id: Optional[int] = None
    proxy_exit_ip: Optional[str] = None
    proxy_error: Optional[str] = None


class AdminRunOut(AdminRunBase):
    id: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    pages_planned: int
    pages_done: int
    items_found: int
    items_staged: int
    error_summary: Optional[str] = None
    debug_json: Optional[dict] = None
    proxy_id: Optional[int] = None
    proxy_exit_ip: Optional[str] = None
    proxy_error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Staged Listing Attribute Schemas
# ============================================================================

class StagedListingAttributeBase(BaseModel):
    key: str
    value_text: Optional[str] = None
    value_num: Optional[float] = None
    value_bool: Optional[bool] = None
    unit: Optional[str] = None


class StagedListingAttributeCreate(StagedListingAttributeBase):
    staged_listing_id: int


class StagedListingAttributeOut(StagedListingAttributeBase):
    id: int
    staged_listing_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Staged Listing Schemas
# ============================================================================

class StagedListingBase(BaseModel):
    source_key: str = Field(..., max_length=100)
    source_listing_id: Optional[str] = Field(None, max_length=255)
    canonical_url: str
    title: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    price_amount: Optional[float] = None
    currency: str = Field(default="USD", max_length=10)
    confidence_score: Optional[float] = None
    odometer_value: Optional[int] = None
    location: Optional[str] = Field(None, max_length=255)
    listed_at: Optional[datetime] = None
    sale_datetime: Optional[datetime] = None
    status: str = Field(default="unknown", pattern="^(active|ended|unknown)$")
    auto_approved: bool = False


class StagedListingCreate(StagedListingBase):
    run_id: int
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class StagedListingOut(StagedListingBase):
    id: int
    run_id: int
    fetched_at: datetime
    created_at: datetime
    updated_at: datetime
    auto_approved: bool
    confidence_score: Optional[float] = None
    attributes: List[StagedListingAttributeOut] = []

    class Config:
        from_attributes = True


# ============================================================================
# Merged Listing Attribute Schemas
# ============================================================================

class MergedListingAttributeBase(BaseModel):
    key: str
    value_text: Optional[str] = None
    value_num: Optional[float] = None
    value_bool: Optional[bool] = None
    unit: Optional[str] = None


class MergedListingAttributeCreate(MergedListingAttributeBase):
    listing_id: int


class MergedListingAttributeOut(MergedListingAttributeBase):
    id: int
    listing_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Merged Listing Schemas
# ============================================================================

class MergedListingBase(BaseModel):
    source_key: str = Field(..., max_length=100)
    source_listing_id: Optional[str] = Field(None, max_length=255)
    canonical_url: str
    title: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    price_amount: Optional[float] = None
    currency: str = Field(default="USD", max_length=10)
    confidence_score: Optional[float] = None
    odometer_value: Optional[int] = None
    location: Optional[str] = Field(None, max_length=255)
    listed_at: Optional[datetime] = None
    sale_datetime: Optional[datetime] = None
    status: str = Field(default="unknown", pattern="^(active|ended|unknown)$")


class MergedListingCreate(MergedListingBase):
    fetched_at: datetime
    merged_at: datetime = Field(default_factory=datetime.utcnow)


class MergedListingOut(MergedListingBase):
    id: int
    fetched_at: datetime
    merged_at: datetime
    created_at: datetime
    updated_at: datetime
    attributes: List[MergedListingAttributeOut] = []

    class Config:
        from_attributes = True
