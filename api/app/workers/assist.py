from datetime import datetime, timedelta
from sqlalchemy import func

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services import assist_service, plan_service
from app.models.assist_case import AssistCase
from app.models.user import User


@celery_app.task
def run_case(case_id: int):
    db = SessionLocal()
    try:
        case = db.get(AssistCase, case_id)
        if not case:
            return "missing"
        user = db.get(User, case.user_id)
        if not user or not user.is_active:
            return "user_inactive"
        assist_service.run_case_inline(db, case, user)
        return "ok"
    finally:
        db.close()


@celery_app.task
def enqueue_due_watch_cases():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_cases = (
            db.query(AssistCase)
            .filter(
                AssistCase.mode == "watch",
                AssistCase.is_active.is_(True),
                AssistCase.next_run_at.isnot(None),
                AssistCase.next_run_at <= now,
                func.coalesce(AssistCase.enqueue_locked_until, datetime(1970, 1, 1)) <= now,
                AssistCase.status.in_(["queued", "completed", "failed"]),
            )
            .all()
        )

        for case in due_cases:
            user = db.get(User, case.user_id)
            if not user or not user.is_active:
                case.is_active = False
                db.add(case)
                db.commit()
                continue

            plan = plan_service.get_active_plan(db, user)
            limits = assist_service.plan_limits(plan)
            if not limits.get("watch_enabled"):
                case.is_active = False
                db.add(case)
                db.commit()
                continue

            # per-user active watch cases
            max_cases = limits.get("watch_max_cases")
            if max_cases is not None:
                active_watch = (
                    db.query(func.count(AssistCase.id))
                    .filter(
                        AssistCase.user_id == user.id,
                        AssistCase.mode == "watch",
                        AssistCase.is_active.is_(True),
                    )
                    .scalar()
                    or 0
                )
                if active_watch > max_cases:
                    case.is_active = False
                    db.add(case)
                    db.commit()
                    continue

            # per-user runs per day
            runs_today_limit = limits.get("watch_runs_per_day")
            if runs_today_limit is not None:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                cases = (
                    db.query(AssistCase)
                    .filter(
                        AssistCase.user_id == user.id,
                        AssistCase.mode == "watch",
                    )
                    .all()
                )
                total_runs_today = 0
                for c in cases:
                    assist_service._reset_runs(c)
                    db.add(c)
                    if c.last_run_at and c.last_run_at >= today_start:
                        total_runs_today += c.runs_today or 0
                db.commit()
                if total_runs_today >= runs_today_limit:
                    case.next_run_at = today_start + timedelta(days=1, minutes=1)
                    db.add(case)
                    db.commit()
                    continue

            # enqueue
            case.enqueue_locked_until = now + timedelta(minutes=5)
            case.status = "queued"
            db.add(case)
            db.commit()
            run_case.delay(case.id)

        return {"enqueued": len(due_cases)}
    finally:
        db.close()
