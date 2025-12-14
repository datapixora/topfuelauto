from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint

from app.core.database import Base


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    usage_date = Column(Date, nullable=False)
    search_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_daily_usage_user_date"),)
