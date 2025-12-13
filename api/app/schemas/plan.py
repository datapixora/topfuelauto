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
    is_active: Optional[bool] = None

    @validator("features", "quotas")
    def ensure_object(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("must be an object")
        return v


class PlanListResponse(BaseModel):
    plans: List[PlanOut]
