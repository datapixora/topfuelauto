from datetime import datetime, timedelta

from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.saved_search_alert import SavedSearchAlert
from app.models.user import User
from app.services import alert_service, plan_service
from app.workers.celery_app import celery_app


@celery_app.task
def run_alert(alert_id: int):
    db = SessionLocal()
    try:
        alert = db.get(SavedSearchAlert, alert_id)
        if not alert or not alert.is_active:
            return "skipped"
        user = db.get(User, alert.user_id)
        if not user or not user.is_active:
            alert.is_active = False
            db.add(alert)
            db.commit()
            return "user_inactive"
        return alert_service.run_alert(db, alert, user)
    finally:
        db.close()


@celery_app.task
def enqueue_due_alerts():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_alerts = (
            db.query(SavedSearchAlert)
            .filter(
                SavedSearchAlert.is_active.is_(True),
                SavedSearchAlert.next_run_at.isnot(None),
                SavedSearchAlert.next_run_at <= now,
                func.coalesce(SavedSearchAlert.enqueue_locked_until, datetime(1970, 1, 1)) <= now,
            )
            .all()
        )

        enqueued = 0
        for alert in due_alerts:
            user = db.get(User, alert.user_id)
            if not user or not user.is_active:
                alert.is_active = False
                db.add(alert)
                db.commit()
                continue

            plan = plan_service.get_active_plan(db, user)
            limits = alert_service.plan_limits(plan)
            if not limits.get("alerts_enabled"):
                alert.is_active = False
                db.add(alert)
                db.commit()
                continue

            max_active = limits.get("alerts_max_active")
            if max_active is not None:
                active_count = (
                    db.query(func.count(SavedSearchAlert.id))
                    .filter(SavedSearchAlert.user_id == user.id, SavedSearchAlert.is_active.is_(True))
                    .scalar()
                    or 0
                )
                if active_count > max_active:
                    alert.is_active = False
                    db.add(alert)
                    db.commit()
                    continue

            alert.enqueue_locked_until = now + timedelta(minutes=5)
            db.add(alert)
            db.commit()
            run_alert.delay(alert.id)
            enqueued += 1

        return {"enqueued": enqueued}
    finally:
        db.close()
