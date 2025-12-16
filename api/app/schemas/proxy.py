from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProxyBase(BaseModel):
    name: str = Field(..., max_length=255)
    host: str = Field(..., max_length=255)
    port: int = Field(default=3120, ge=1)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, max_length=255)
    scheme: str = Field(default="http", max_length=10)
    is_enabled: bool = True
    weight: int = Field(default=1, ge=1)
    max_concurrency: int = Field(default=1, ge=1)
    region: Optional[str] = Field(None, max_length=100)


class ProxyCreate(ProxyBase):
    pass


class ProxyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    host: Optional[str] = Field(None, max_length=255)
    port: Optional[int] = Field(None, ge=1)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, max_length=255)  # replace if provided
    scheme: Optional[str] = Field(None, max_length=10)
    is_enabled: Optional[bool] = None
    weight: Optional[int] = Field(None, ge=1)
    max_concurrency: Optional[int] = Field(None, ge=1)
    region: Optional[str] = Field(None, max_length=100)


class ProxyOut(BaseModel):
    id: int
    name: str
    host: str
    port: int
    username: Optional[str] = None
    scheme: str
    is_enabled: bool
    weight: int
    max_concurrency: int
    region: Optional[str] = None
    last_check_at: Optional[datetime] = None
    last_check_status: Optional[str] = None
    last_exit_ip: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
