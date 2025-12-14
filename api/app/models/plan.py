from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    price_monthly = Column(Integer, nullable=True)
    features = Column(JSONB, nullable=True)
    quotas = Column(JSONB, nullable=True)
    searches_per_day = Column(Integer, nullable=True)
    quota_reached_message = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
