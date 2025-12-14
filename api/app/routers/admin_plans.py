from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.plan import Plan
from app.models.user import User
from app.schemas.plan import PlanListResponse, PlanOut, PlanUpdate

router = APIRouter(prefix="/api/v1/admin", tags=["admin-plans"])


@router.get("/plans", response_model=PlanListResponse)
def list_admin_plans(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Return plans from the database ordered by id."""
    plans = db.query(Plan).order_by(Plan.id.asc()).all()
    return {"plans": plans}


@router.patch("/plans/{plan_id}", response_model=PlanOut)
def update_admin_plan(
    plan_id: int,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plans/public", response_model=PlanListResponse)
def list_public_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.id.asc()).all()
    return {"plans": plans}
