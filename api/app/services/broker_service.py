from sqlalchemy.orm import Session

from app.models.broker_lead import BrokerLead


def create_lead(db: Session, user_id: int, listing_id: int, destination_country: str, full_name: str, phone: str, max_bid=None) -> BrokerLead:
    lead = BrokerLead(
        user_id=user_id,
        listing_id=listing_id,
        destination_country=destination_country,
        full_name=full_name,
        phone=phone,
        max_bid=max_bid,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def get_user_leads(db: Session, user_id: int):
    return db.query(BrokerLead).filter(BrokerLead.user_id == user_id).order_by(BrokerLead.created_at.desc()).all()