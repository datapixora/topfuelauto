from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint

from app.core.database import Base


class ProviderSetting(Base):
    __tablename__ = "provider_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_provider_settings_key"),)

    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True)
    enabled = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)
    mode = Column(String(16), nullable=False, default="both")  # search | assist | both
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
