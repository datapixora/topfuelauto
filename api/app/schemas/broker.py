from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class BrokerRequest(BaseModel):
    listing_id: int
    max_bid: Decimal | None = None
    destination_country: str
    full_name: str
    phone: str


class BrokerLeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    listing_id: int
    destination_country: str
    full_name: str
    phone: str
    status: str