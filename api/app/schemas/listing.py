from datetime import datetime
from pydantic import BaseModel, ConfigDict
from decimal import Decimal


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    make: str
    model: str
    trim: str | None = None
    year: int


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    price: Decimal | None = None
    currency: str | None = None
    location: str | None = None
    end_date: datetime | None = None
    condition: str | None = None
    transmission: str | None = None
    mileage: int | None = None
    risk_flags: list | None = None
    vehicle: VehicleOut


class ListingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    price: Decimal | None = None
    currency: str | None = None
    location: str | None = None
    end_date: datetime | None = None
    vehicle: VehicleOut