import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.alert_match import AlertMatch
from app.models.notification import InAppNotification
from app.models.plan import Plan
from app.models.saved_search_alert import SavedSearchAlert
from app.models.user import User
from app.providers import get_active_providers
from app.services import plan_service

DEFAULT_ALERT_SAMPLE_SIZE = 20
DEFAULT_ALERT_CADENCE_MINUTES = 1440  # daily fallback
ENQUEUE_LOCK_MINUTES = 5


def plan_limits(plan: Plan | None) -> Dict[str, Any]:
    quotas = plan.quotas if plan and isinstance(plan.quotas, dict) else {}
    sample_size = None
    if isinstance(quotas, dict):
        sample_size = quotas.get("alert_sample_size")
    return {
        "alerts_enabled": bool(plan and plan.alerts_enabled),
        "alerts_max_active": plan.alerts_max_active if plan else None,
        "alerts_cadence_minutes": plan.alerts_cadence_minutes if plan else None,
        "sample_size": sample_size,
    }


def _ensure_plan_allows_alert(db: Session, user: User) -> Tuple[Plan | None, Dict[str, Any]]:
    plan = plan_service.get_active_plan(db, user)
    limits = plan_limits(plan)
    if not limits.get("alerts_enabled"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Alerts are not enabled for this plan.")
    max_active = limits.get("alerts_max_active")
    if max_active is not None:
        active_count = (
            db.query(func.count(SavedSearchAlert.id))
            .filter(SavedSearchAlert.user_id == user.id, SavedSearchAlert.is_active.is_(True))
            .scalar()
            or 0
        )
        if active_count >= max_active:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You have reached the maximum active alerts for your plan.",
            )
    return plan, limits


def _compute_name_from_query(query: Dict[str, Any]) -> str:
    parts: List[str] = []
    if query.get("make"):
        parts.append(str(query.get("make")))
    if query.get("model"):
        parts.append(str(query.get("model")))
    if query.get("q"):
        parts.append(str(query.get("q")))
    if not parts:
        return "Saved search"
    return " ".join(parts)


def create_alert(db: Session, user: User, query_json: Dict[str, Any], name: str | None, is_active: bool = True):
    plan, limits = _ensure_plan_allows_alert(db, user)
    if not query_json or not any(query_json.get(k) for k in ["q", "query", "make", "model"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide a query, make, or model for the alert.")
    cadence = limits.get("alerts_cadence_minutes") or DEFAULT_ALERT_CADENCE_MINUTES
    alert = SavedSearchAlert(
        user_id=user.id,
        name=name or _compute_name_from_query(query_json),
        query_json=query_json,
        is_active=is_active,
        cadence_minutes=cadence,
        next_run_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts(db: Session, user: User):
    return (
        db.query(SavedSearchAlert)
        .filter(SavedSearchAlert.user_id == user.id)
        .order_by(SavedSearchAlert.created_at.desc())
        .all()
    )


def get_alert(db: Session, user: User, alert_id: int) -> SavedSearchAlert:
    alert = db.get(SavedSearchAlert, alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


def update_alert(
    db: Session,
    user: User,
    alert_id: int,
    *,
    name: str | None = None,
    is_active: bool | None = None,
) -> SavedSearchAlert:
    alert = get_alert(db, user, alert_id)
    if name is not None:
        alert.name = name
    if is_active is not None:
        alert.is_active = is_active
    if alert.is_active and alert.next_run_at is None:
        alert.next_run_at = datetime.utcnow()
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def delete_alert(db: Session, user: User, alert_id: int):
    alert = get_alert(db, user, alert_id)
    alert.is_active = False
    alert.next_run_at = None
    db.add(alert)
    db.commit()


def compute_next_run(alert: SavedSearchAlert, limits: Dict[str, Any]) -> datetime:
    cadence = limits.get("alerts_cadence_minutes") or alert.cadence_minutes or DEFAULT_ALERT_CADENCE_MINUTES
    return datetime.utcnow() + timedelta(minutes=cadence)


def _hash_results(items: List[Dict[str, Any]]) -> str:
    payload = [
        {
            "id": item.get("id"),
            "price": item.get("price"),
            "url": item.get("url"),
            "title": item.get("title"),
        }
        for item in items
    ]
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def _execute_search(query_json: Dict[str, Any], sample_size: int) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
    settings = get_settings()
    providers = get_active_providers(settings)
    if not providers:
        return [], 0, []

    q = query_json.get("q") or query_json.get("query") or ""
    filters = {
        "make": query_json.get("make"),
        "model": query_json.get("model"),
        "year_min": query_json.get("year_min"),
        "year_max": query_json.get("year_max"),
        "price_min": query_json.get("price_min"),
        "price_max": query_json.get("price_max"),
        "location": query_json.get("location"),
        "sort": query_json.get("sort"),
    }

    items: List[Dict[str, Any]] = []
    total = 0
    sources: List[Dict[str, Any]] = []
    for provider in providers:
        provider_items, provider_total, meta = provider.search_listings(
            query=q,
            filters=filters,
            page=1,
            page_size=sample_size,
        )
        items.extend(provider_items[:sample_size])
        total += provider_total
        sources.append(meta)

    items = items[:sample_size]
    return items, total, sources


def _create_notification(db: Session, user_id: int, title: str, body: str | None, link_url: str | None):
    notif = InAppNotification(
        user_id=user_id,
        type="alert_match",
        title=title,
        body=body,
        link_url=link_url,
    )
    db.add(notif)


def run_alert(db: Session, alert: SavedSearchAlert, user: User):
    plan = plan_service.get_active_plan(db, user)
    limits = plan_limits(plan)
    if not limits.get("alerts_enabled"):
        alert.is_active = False
        db.add(alert)
        db.commit()
        return {"status": "disabled"}

    # enforce active limit again in case plan changed
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
            return {"status": "over_limit"}

    sample_size = limits.get("sample_size") or DEFAULT_ALERT_SAMPLE_SIZE

    items, total, _sources = _execute_search(alert.query_json or {}, sample_size)
    now = datetime.utcnow()

    new_hash = _hash_results(items) if items else None
    existing_hash = alert.last_result_hash

    new_ids: List[str] = []
    if new_hash and new_hash != existing_hash:
        existing_matches = {
            row[0]
            for row in db.query(AlertMatch.listing_id).filter(AlertMatch.alert_id == alert.id).all()
        }
        for item in items:
            if not item.get("id"):
                continue
            if item["id"] in existing_matches:
                continue
            raw_price = item.get("price")
            price_val = None
            if isinstance(raw_price, (int, float)):
                price_val = int(raw_price)
            match = AlertMatch(
                alert_id=alert.id,
                user_id=user.id,
                listing_id=item.get("id"),
                listing_url=item.get("url"),
                title=item.get("title"),
                price=price_val,
                location=item.get("location"),
                matched_at=now,
            )
            db.add(match)
            new_ids.append(item["id"])

        if new_ids:
            _create_notification(
                db,
                user.id,
                title=f"{len(new_ids)} new matches for {alert.name or 'alert'}",
                body=None,
                link_url=f"/account/alerts/{alert.id}",
            )

    alert.last_run_at = now
    alert.last_result_hash = new_hash
    alert.next_run_at = compute_next_run(alert, limits)
    alert.enqueue_locked_until = None
    db.add(alert)
    db.commit()
    return {"status": "ok", "total": total, "new": len(new_ids)}


def alert_detail_with_matches(db: Session, user: User, alert_id: int):
    alert = get_alert(db, user, alert_id)
    matches = (
        db.query(AlertMatch)
        .filter(AlertMatch.alert_id == alert.id)
        .order_by(AlertMatch.matched_at.desc())
        .limit(100)
        .all()
    )
    # mark viewed
    for m in matches:
        if m.is_new:
            m.is_new = False
            db.add(m)
    db.commit()
    return alert, matches


def list_notifications(db: Session, user: User, limit: int = 20):
    notifications = (
        db.query(InAppNotification)
        .filter(InAppNotification.user_id == user.id)
        .order_by(InAppNotification.created_at.desc())
        .limit(limit)
        .all()
    )
    unread_count = (
        db.query(func.count(InAppNotification.id))
        .filter(InAppNotification.user_id == user.id, InAppNotification.is_read.is_(False))
        .scalar()
        or 0
    )
    return notifications, unread_count


def mark_notification_read(db: Session, user: User, notification_id: int):
    notif = db.get(InAppNotification, notification_id)
    if not notif or notif.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notif.is_read = True
    db.add(notif)
    db.commit()
    return notif


def mark_all_notifications_read(db: Session, user: User):
    db.query(InAppNotification).filter(
        InAppNotification.user_id == user.id, InAppNotification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
