from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    name: Optional[str] = None
    query: Dict[str, Any] = Field(default_factory=dict)
    is_active: Optional[bool] = True


class AlertUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class AlertMatchOut(BaseModel):
    id: int
    listing_id: str
    listing_url: Optional[str] = None
    title: Optional[str] = None
    price: Optional[int] = None
    location: Optional[str] = None
    is_new: bool
    matched_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class AlertOut(BaseModel):
    id: int
    name: Optional[str] = None
    query_json: Dict[str, Any]
    is_active: bool
    cadence_minutes: Optional[int] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_result_hash: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class AlertDetailResponse(BaseModel):
    alert: AlertOut
    matches: List[AlertMatchOut]


class AlertListResponse(BaseModel):
    alerts: List[AlertOut]


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: Optional[str] = None
    link_url: Optional[str] = None
    is_read: bool
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationOut]
    unread_count: int
