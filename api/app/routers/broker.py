from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services import broker_service
from app.schemas import broker as broker_schema

router = APIRouter(prefix="/api/v1/broker", tags=["broker"])


@router.post("/request-bid", response_model=broker_schema.BrokerLeadOut)
def request_bid(payload: broker_schema.BrokerRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lead = broker_service.create_lead(
        db,
        user_id=current_user.id,
        listing_id=payload.listing_id,
        destination_country=payload.destination_country,
        full_name=payload.full_name,
        phone=payload.phone,
        max_bid=payload.max_bid,
    )
    return lead


@router.get("/leads/me", response_model=list[broker_schema.BrokerLeadOut])
def my_leads(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    leads = broker_service.get_user_leads(db, current_user.id)
    return leads