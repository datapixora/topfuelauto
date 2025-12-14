from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import auth as auth_schema
from app.services import auth_service
from app.core.security import get_current_user
from app.services import usage_service
from app.models.plan import Plan

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", response_model=auth_schema.Token)
def signup(payload: auth_schema.UserCreate, db: Session = Depends(get_db)):
    user = auth_service.create_user(db, payload.email, payload.password)
    token = auth_service.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=auth_schema.Token)
def login(payload: auth_schema.UserLogin, db: Session = Depends(get_db)):
    token = auth_service.authenticate_user(db, payload.email, payload.password)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=auth_schema.UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.get("/me/quota")
def quota(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    plan_key = "pro" if getattr(current_user, "is_pro", False) else "free"
    plan = db.query(Plan).filter(Plan.key == plan_key, Plan.is_active.is_(True)).first()
    plan_limit = plan.searches_per_day if plan and plan.searches_per_day is not None else None
    if plan_limit is None and plan_key == "free":
        plan_limit = 5

    usage = usage_service.get_or_create_today_usage(db, current_user.id)
    remaining = None
    if plan_limit is not None:
        remaining = max(plan_limit - usage.search_count, 0)
    reset_at = (
        datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if plan_limit is not None
        else None
    )

    return {
        "limit": plan_limit,
        "used": usage.search_count,
        "remaining": remaining,
        "reset_at": reset_at.isoformat() if reset_at else None,
    }
