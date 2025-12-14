from typing import Optional
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.user import User


def get_active_plan(db: Session, user: User) -> Optional[Plan]:
    """Return the active plan for a user. Falls back to active 'free' plan, then any active plan."""
    if user.current_plan_id:
        plan = db.get(Plan, user.current_plan_id)
        if plan and plan.is_active:
            return plan

    plan = db.query(Plan).filter(Plan.key == "free", Plan.is_active.is_(True)).first()
    if plan:
        return plan

    return db.query(Plan).filter(Plan.is_active.is_(True)).first()


def assign_plan(db: Session, user: User, plan: Plan) -> None:
    user.current_plan_id = plan.id
    db.add(user)

