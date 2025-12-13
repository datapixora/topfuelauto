from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class BrokerLead(Base):
    __tablename__ = "broker_leads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)

    max_bid = Column(Numeric(12, 2), nullable=True)
    destination_country = Column(String(100), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    status = Column(String(50), default="NEW")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="leads")
    listing = relationship("Listing", back_populates="leads")