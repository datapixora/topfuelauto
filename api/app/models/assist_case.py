from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AssistCase(Base):
    __tablename__ = "assist_cases"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    mode = Column(String(16), nullable=False, default="one_shot")
    intake_version = Column(Integer, nullable=False, default=1)
    intake_payload = Column(JSON, nullable=True)
    normalized_payload = Column(JSON, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    runs_today = Column(Integer, nullable=False, default=0)
    next_allowed_run_at = Column(DateTime, nullable=True)
    budget_cents_limit = Column(Integer, nullable=True)
    budget_cents_used = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    enqueue_locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    steps = relationship("AssistStep", back_populates="case", lazy="select")
