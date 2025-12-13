from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import relationship

from app.core.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), default="internal")
    source_url = Column(String(500), nullable=True)
    title = Column(String(255), nullable=False, index=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    vehicle = relationship("Vehicle", back_populates="listings")

    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), default="USD")
    location = Column(String(255), nullable=True)
    end_date = Column(DateTime, nullable=True)
    condition = Column(String(50), nullable=True)
    transmission = Column(String(50), nullable=True)
    mileage = Column(Integer, nullable=True)
    risk_flags = Column(JSONB, default=list)

    search_text = Column(Text, nullable=True)
    search_tsv = Column(TSVECTOR, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_history = relationship("PriceHistory", back_populates="listing")
    leads = relationship("BrokerLead", back_populates="listing")