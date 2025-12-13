from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class SearchQuery(BaseModel):
    q: str
    year_min: int | None = None
    year_max: int | None = None
    price_min: int | None = None
    price_max: int | None = None
    location: str | None = None
    condition: str | None = None
    transmission: str | None = None
    sort: str | None = None


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    listing_id: int
    title: str
    year: int
    make: str
    model: str
    trim: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    location: str | None = None
    end_date: datetime | None = None
    risk_flags: list | None = None
    score: float | None = None