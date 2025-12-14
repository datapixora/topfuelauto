from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text

from app.core.database import Base


class AssistArtifact(Base):
    __tablename__ = "assist_artifacts"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("assist_cases.id"), nullable=False)
    type = Column(String(100), nullable=False)
    content_text = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
