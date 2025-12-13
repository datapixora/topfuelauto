from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class VinReport(Base):
    __tablename__ = "vin_reports"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String(32), index=True, nullable=False)
    report_type = Column(String(50), nullable=False)
    payload_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)