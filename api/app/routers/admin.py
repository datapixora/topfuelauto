from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.search_event import SearchEvent
from app.models.user import User
from app.models.broker_lead import BrokerLead
from app.models.listing import Listing

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/metrics/overview")
def metrics_overview(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_users = db.query(User).count()
    admins = db.query(User).filter(User.is_admin.is_(True)).count()
    searches_today = (
        db.query(SearchEvent).count()
    )  # TODO: restrict to today when data populated
    return {
        "total_users": total_users,
        "admins": admins,
        "searches_today": searches_today,
        "mrr": 0,  # TODO: compute from subscriptions when available
        "active_subscriptions": 0,  # TODO
        "new_signups": 0,  # TODO
        "provider_health": [],
    }


@router.get("/metrics/users")
def metrics_users(range: str = "30d", db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total = db.query(User).count()
    users = db.query(User).limit(100).all()
    return {"range": range, "total": total, "users": [{"id": u.id, "email": u.email, "is_pro": u.is_pro, "is_admin": u.is_admin} for u in users]}


@router.get("/metrics/subscriptions")
def metrics_subscriptions(range: str = "30d", admin: User = Depends(get_current_admin)):
    # TODO: implement when subscription data is available
    return {"range": range, "series": [], "by_plan": [], "subscriptions": []}


@router.get("/metrics/searches")
def metrics_searches(range: str = "30d", db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    top = (
        db.query(SearchEvent.query, SearchEvent.results_count)
        .order_by(SearchEvent.created_at.desc())
        .limit(10)
        .all()
    )
    top_list = [{"query": q, "results_count": rc} for q, rc in top]
    return {"range": range, "top_queries": top_list, "series": []}


@router.get("/providers/status")
def providers_status(admin: User = Depends(get_current_admin)):
    # TODO: wire to real provider sync status
    return {"providers": []}


@router.get("/users/{user_id}")
def admin_user_detail(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.get(User, user_id)
    if not user:
        return {"error": "not found"}
    return {"id": user.id, "email": user.email, "is_pro": user.is_pro, "is_admin": user.is_admin}


@router.get("/subscriptions")
def admin_subscriptions(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    # Placeholder until subscriptions table exists
    return {"subscriptions": []}
