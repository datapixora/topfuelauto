from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProviderSettingOut(BaseModel):
    key: str
    enabled: bool
    priority: int
    mode: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ProviderSettingUpdate(BaseModel):
    enabled: Optional[bool] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=0)
    mode: Optional[str] = Field(default=None)
