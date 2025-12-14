from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    # Deprecated: do not use for enforcement; active plan/subscription is source of truth
    is_pro = Column(Boolean, default=False)
    current_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    leads = relationship("BrokerLead", back_populates="user")
