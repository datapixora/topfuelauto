from fastapi import APIRouter, Depends

from app.core.security import get_current_admin
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin-plans"])


@router.get("/plans")
def list_admin_plans(admin: User = Depends(get_current_admin)):
    """Temporary hardcoded plans to avoid 404 while backing store is wired."""
    plans = [
        {
            "id": 1,
            "key": "free",
            "name": "Free",
            "price_monthly": None,
            "description": "Starter plan",
            "features": {"vin_history": False},
            "quotas": {"searches_per_day": 25},
            "is_active": True,
        },
        {
            "id": 2,
            "key": "pro",
            "name": "Pro",
            "price_monthly": 39,
            "description": "For frequent buyers",
            "features": {"vin_history": True, "priority_support": True},
            "quotas": {"searches_per_day": 250},
            "is_active": True,
        },
        {
            "id": 3,
            "key": "ultimate",
            "name": "Ultimate",
            "price_monthly": 99,
            "description": "High volume",
            "features": {"vin_history": True, "priority_support": True, "bulk": True},
            "quotas": {"searches_per_day": 1000},
            "is_active": True,
        },
    ]
    return {"plans": plans}
