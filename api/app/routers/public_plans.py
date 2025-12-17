from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.plan import Plan
from app.schemas.plan import PublicPlanListResponse, PublicPlanOut

router = APIRouter(prefix="/api/v1/public", tags=["public"])


def _normalize_features(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out
    if isinstance(value, dict):
        out = []
        for k, enabled in value.items():
            if enabled:
                out.append(str(k))
        return out
    return []


@router.get("/plans", response_model=PublicPlanListResponse)
def list_public_plans(db: Session = Depends(get_db)):
    """
    Public plans endpoint for marketing pages.

    - Returns active plans only
    - Sorted by sort_order asc, then created_at asc
    """
    plans = (
        db.query(Plan)
        .filter(Plan.is_active.is_(True))
        .order_by(Plan.sort_order.asc(), Plan.created_at.asc())
        .all()
    )

    out: list[PublicPlanOut] = []
    for plan in plans:
        out.append(
            PublicPlanOut(
                id=plan.id,
                slug=plan.slug or plan.key,
                name=plan.name,
                price_monthly=plan.price_monthly,
                currency="USD",
                description=plan.description,
                features=_normalize_features(plan.features),
                is_featured=bool(getattr(plan, "is_featured", False)),
                is_active=bool(plan.is_active),
                sort_order=int(getattr(plan, "sort_order", 0) or 0),
            )
        )

    return {"plans": out}

