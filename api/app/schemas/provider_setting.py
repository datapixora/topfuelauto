from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProviderSettingOut(BaseModel):
    key: str
    enabled: bool
    priority: int
    mode: str
    settings_json: dict | None = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ProviderSettingUpdate(BaseModel):
    enabled: Optional[bool] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=0)
    mode: Optional[str] = Field(default=None)
    settings_json: Optional[dict] = Field(default=None)


class WebCrawlProviderConfig(BaseModel):
    enabled: bool
    priority: int
    allowlist: list[str]
    rate_per_minute: int
    concurrency: int
    max_sources: int
    min_results: int


class WebCrawlProviderConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0)
    allowlist: Optional[list[str]] = None
    rate_per_minute: Optional[int] = Field(default=None, ge=1)
    concurrency: Optional[int] = Field(default=None, ge=1)
    max_sources: Optional[int] = Field(default=None, ge=1)
    min_results: Optional[int] = Field(default=None, ge=0)
