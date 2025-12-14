from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON

from app.core.database import Base


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    stripe_event_id = Column(String(255), nullable=False, unique=True)
    type = Column(String(100), nullable=False)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
