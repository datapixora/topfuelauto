from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator


class PlanOut(BaseModel):
    id: int
    key: str
    name: str
    price_monthly: Optional[int] = None
    description: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    quotas: Optional[Dict[str, Any]] = None
    searches_per_day: Optional[int] = None
    quota_reached_message: Optional[str] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price_monthly: Optional[int] = None
    description: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    quotas: Optional[Dict[str, Any]] = None
    searches_per_day: Optional[int] = None
    quota_reached_message: Optional[str] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("features", "quotas")
    def ensure_object(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("must be an object")
        return v

    @validator("searches_per_day")
    def non_negative(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("searches_per_day must be >= 0")
        return v

    @validator("stripe_price_id_monthly", "stripe_price_id_yearly")
    def stripe_price_format(cls, v):
        if v is None:
            return v
        if len(v) > 100:
            raise ValueError("stripe price id too long")
        return v

    @validator("quota_reached_message")
    def message_length(cls, v):
        if v is None:
            return v
        if len(v) > 2800:
            raise ValueError("quota_reached_message too long (max 2800 chars)")
        return v


class PlanListResponse(BaseModel):
    plans: List[PlanOut]
