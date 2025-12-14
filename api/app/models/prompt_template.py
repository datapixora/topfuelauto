from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text

from app.core.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    role = Column(String(32), nullable=False)
    template = Column(Text, nullable=False)
    schema_json = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
