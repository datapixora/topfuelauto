from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    listing = relationship("Listing", back_populates="price_history")

    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="USD")
    ts = Column(DateTime, default=datetime.utcnow)