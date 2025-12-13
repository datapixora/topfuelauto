from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    make = Column(String(100), index=True, nullable=False)
    model = Column(String(100), index=True, nullable=False)
    trim = Column(String(100), index=True, nullable=True)
    year = Column(Integer, index=True, nullable=False)

    listings = relationship("Listing", back_populates="vehicle")