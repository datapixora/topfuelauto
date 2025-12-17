from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator


class PlanOut(BaseModel):
    id: int
    key: str
    slug: str
    name: str
    price_monthly: Optional[int] = None
    description: Optional[str] = None
    features: List[str] = []
    quotas: Optional[Dict[str, Any]] = None
    searches_per_day: Optional[int] = None
    quota_reached_message: Optional[str] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    assist_one_shot_per_day: Optional[int] = None
    assist_watch_enabled: Optional[bool] = None
    assist_watch_max_cases: Optional[int] = None
    assist_watch_runs_per_day: Optional[int] = None
    assist_ai_budget_cents_per_day: Optional[int] = None
    assist_reruns_per_day: Optional[int] = None
    alerts_enabled: Optional[bool] = None
    alerts_max_active: Optional[int] = None
    alerts_cadence_minutes: Optional[int] = None
    is_active: bool
    is_featured: bool = False
    sort_order: int = 0
    created_at: datetime

    class Config:
        orm_mode = True

    @validator("features", pre=True)
    def normalize_features(cls, v):
        """
        Normalize plan.features to a list of strings for public display.

        Back-compat: some environments may still have features stored as a JSON object.
        """
        if v is None:
            return []
        if isinstance(v, list):
            out = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
            return out
        if isinstance(v, dict):
            out = []
            for key, enabled in v.items():
                if enabled:
                    out.append(str(key))
            return out
        return []


class PlanUpdate(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    price_monthly: Optional[int] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    quotas: Optional[Dict[str, Any]] = None
    searches_per_day: Optional[int] = None
    quota_reached_message: Optional[str] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    assist_one_shot_per_day: Optional[int] = None
    assist_watch_enabled: Optional[bool] = None
    assist_watch_max_cases: Optional[int] = None
    assist_watch_runs_per_day: Optional[int] = None
    assist_ai_budget_cents_per_day: Optional[int] = None
    assist_reruns_per_day: Optional[int] = None
    alerts_enabled: Optional[bool] = None
    alerts_max_active: Optional[int] = None
    alerts_cadence_minutes: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None

    @validator("slug")
    def slug_format(cls, v):
        if v is None:
            return v
        s = v.strip()
        if not s:
            raise ValueError("slug must be a non-empty string")
        if len(s) > 50:
            raise ValueError("slug too long (max 50 chars)")
        return s

    @validator("sort_order")
    def sort_order_non_negative(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("sort_order must be >= 0")
        return v

    @validator("quotas")
    def ensure_object(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("must be an object")
        return v

    @validator("features")
    def ensure_features_array(cls, v):
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("features must be an array of strings")
        out: list[str] = []
        for item in v:
            if not isinstance(item, str):
                raise ValueError("features must be an array of strings")
            txt = item.strip()
            if txt:
                out.append(txt)
        return out

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

    @validator(
        "assist_one_shot_per_day",
        "assist_watch_max_cases",
        "assist_watch_runs_per_day",
        "assist_ai_budget_cents_per_day",
        "assist_reruns_per_day",
        "alerts_max_active",
        "alerts_cadence_minutes",
    )
    def non_negative_ints(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class PlanListResponse(BaseModel):
    plans: List[PlanOut]


class PublicPlanOut(BaseModel):
    id: int
    slug: str
    name: str
    price_monthly: Optional[int] = None
    currency: str = "USD"
    description: Optional[str] = None
    features: List[str] = []
    is_featured: bool = False
    is_active: bool
    sort_order: int = 0


class PublicPlanListResponse(BaseModel):
    plans: List[PublicPlanOut]
