from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text

from app.core.database import Base


class AssistStep(Base):
    __tablename__ = "assist_steps"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("assist_cases.id"), nullable=False)
    step_key = Column(String(100), nullable=False)
    step_version = Column(Integer, nullable=False, default=1)
    provider = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    token_in = Column(Integer, nullable=True)
    token_out = Column(Integer, nullable=True)
    cost_cents = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
