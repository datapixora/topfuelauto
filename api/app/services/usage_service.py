from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.daily_usage import DailyUsage


def get_or_create_today_usage(db: Session, user_id: int) -> DailyUsage:
    today = datetime.utcnow().date()
    usage = (
        db.query(DailyUsage)
        .filter(DailyUsage.user_id == user_id, DailyUsage.usage_date == today)
        .with_for_update(of=DailyUsage, nowait=False)
        .first()
    )
    if usage:
        return usage
    usage = DailyUsage(user_id=user_id, usage_date=today, search_count=0)
    db.add(usage)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        usage = (
            db.query(DailyUsage)
            .filter(DailyUsage.user_id == user_id, DailyUsage.usage_date == today)
            .with_for_update(of=DailyUsage, nowait=False)
            .first()
        )
    return usage


def increment_search_usage(db: Session, user_id: int) -> DailyUsage:
    usage = get_or_create_today_usage(db, user_id)
    usage.search_count += 1
    usage.updated_at = datetime.utcnow()
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage
