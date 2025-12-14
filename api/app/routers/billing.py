import json
import logging
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.billing_event import BillingEvent
from app.models.plan import Plan
from app.models.user import User
from app.services import plan_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
settings = get_settings()

STRIPE_SECRET = getattr(settings, "stripe_secret_key", None)
STRIPE_WEBHOOK_SECRET = getattr(settings, "stripe_webhook_secret", None)
PUBLIC_WEB_URL = getattr(settings, "public_web_url", "https://topfuelauto.com")

if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET


@router.post("/checkout")
def create_checkout(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not STRIPE_SECRET:
        raise HTTPException(status_code=422, detail={"code": "stripe_not_configured"})

    plan_id = payload.get("plan_id")
    interval: Literal["month", "year"] = payload.get("interval", "month")
    if interval not in ("month", "year"):
        raise HTTPException(status_code=422, detail="Invalid interval")

    plan = db.get(Plan, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")

    price_id = plan.stripe_price_id_monthly if interval == "month" else plan.stripe_price_id_yearly
    if not price_id:
        raise HTTPException(status_code=422, detail={"code": "stripe_price_not_configured"})

    success_url = f"{PUBLIC_WEB_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{PUBLIC_WEB_URL}/pricing?canceled=1"

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=current_user.email,
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={
                "user_id": str(current_user.id),
                "plan_id": str(plan.id),
                "interval": interval,
            },
        )
    except Exception as exc:
        logger.exception("Stripe checkout creation failed")
        raise HTTPException(status_code=500, detail="Unable to start checkout") from exc

    return {"checkout_url": session.url}


def _record_event(db: Session, stripe_event_id: str, event_type: str, user_id: int | None, payload_obj: dict):
    existing = db.query(BillingEvent).filter(BillingEvent.stripe_event_id == stripe_event_id).first()
    if existing:
        return existing
    be = BillingEvent(
        stripe_event_id=stripe_event_id,
        type=event_type,
        user_id=user_id,
        payload_json=payload_obj,
    )
    db.add(be)
    db.commit()
    return be


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not STRIPE_SECRET or not STRIPE_WEBHOOK_SECRET:
        return {"received": False}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    stripe_event_id = event.get("id")

    data_object = event["data"]["object"]
    metadata = data_object.get("metadata", {}) if isinstance(data_object, dict) else {}
    user_id = int(metadata.get("user_id")) if metadata.get("user_id") else None
    plan_id = int(metadata.get("plan_id")) if metadata.get("plan_id") else None

    _record_event(db, stripe_event_id, event_type, user_id, json.loads(payload.decode("utf-8")))

    if event_type == "checkout.session.completed":
        if user_id and plan_id:
            user = db.get(User, user_id)
            plan = db.get(Plan, plan_id)
            if user and plan and plan.is_active:
                plan_service.assign_plan(db, user, plan)
                db.commit()
    elif event_type == "customer.subscription.deleted":
        if user_id:
            user = db.get(User, user_id)
            if user:
                free_plan = db.query(Plan).filter(Plan.key == "free", Plan.is_active.is_(True)).first()
                if free_plan:
                    plan_service.assign_plan(db, user, free_plan)
                    db.commit()

    return {"received": True}
