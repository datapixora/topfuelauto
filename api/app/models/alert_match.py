from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.core.database import Base


class AlertMatch(Base):
    __tablename__ = "alert_matches"

    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("saved_search_alerts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    listing_id = Column(String(128), nullable=False)
    listing_url = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    price = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)
    is_new = Column(Boolean, default=True, nullable=False)
    matched_at = Column(DateTime, default=datetime.utcnow, index=True)
