from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas import alerts as alert_schema
from app.services import alert_service

router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.post("/alerts", response_model=alert_schema.AlertOut)
def create_alert(
    payload: alert_schema.AlertCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    is_active = True if payload.is_active is None else payload.is_active
    alert = alert_service.create_alert(db, current_user, payload.query, payload.name, is_active=is_active)
    return alert


@router.get("/alerts", response_model=alert_schema.AlertListResponse)
def list_alerts(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alerts = alert_service.list_alerts(db, current_user)
    return {"alerts": alerts}


@router.get("/alerts/{alert_id}", response_model=alert_schema.AlertDetailResponse)
def alert_detail(alert_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alert, matches = alert_service.alert_detail_with_matches(db, current_user, alert_id)
    return {"alert": alert, "matches": matches}


@router.patch("/alerts/{alert_id}", response_model=alert_schema.AlertOut)
def update_alert(
    alert_id: int,
    payload: alert_schema.AlertUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    alert = alert_service.update_alert(
        db,
        current_user,
        alert_id,
        name=payload.name,
        is_active=payload.is_active,
    )
    return alert


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alert_service.delete_alert(db, current_user, alert_id)
    return {"status": "deleted"}


@router.get("/notifications", response_model=alert_schema.NotificationListResponse)
def list_notifications(limit: int = 20, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if limit > 100:
        raise HTTPException(status_code=400, detail="Limit too high")
    notifications, unread = alert_service.list_notifications(db, current_user, limit=limit)
    return {"notifications": notifications, "unread_count": unread}


@router.post("/notifications/{notification_id}/read", response_model=alert_schema.NotificationOut)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notif = alert_service.mark_notification_read(db, current_user, notification_id)
    return notif


@router.post("/notifications/read-all")
def read_all_notifications(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alert_service.mark_all_notifications_read(db, current_user)
    return {"status": "ok"}
