from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text, case
from datetime import datetime, timedelta
from typing import List

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.search_event import SearchEvent
from app.models.user import User
from app.models.broker_lead import BrokerLead
from app.models.listing import Listing
from app.models.plan import Plan
from app.models.admin_action_log import AdminActionLog
from app.models.daily_usage import DailyUsage
from app.services import usage_service, plan_service, provider_setting_service
from app.schemas.provider_setting import ProviderSettingOut, ProviderSettingUpdate
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _range_start(range: str) -> datetime:
    now = datetime.utcnow()
    if range == "24h":
        return now - timedelta(hours=24)
    if range == "7d":
        return now - timedelta(days=7)
    if range == "30d":
        return now - timedelta(days=30)
    if range == "90d":
        return now - timedelta(days=90)
    return now - timedelta(days=7)


@router.get("/metrics/overview")
def metrics_overview(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_users = db.query(User).count()
    admins = db.query(User).filter(User.is_admin.is_(True)).count()
    searches = db.query(SearchEvent)
    searches_count = searches.count()
    zero_results = searches.filter(SearchEvent.result_count == 0).count()
    avg_latency = searches.with_entities(func.avg(SearchEvent.latency_ms)).scalar() or 0
    return {
        "total_users": total_users,
        "admins": admins,
        "searches_today": searches_count,
        "zero_results": zero_results,
        "avg_latency_ms": int(avg_latency),
        "mrr": 0,  # TODO: compute from subscriptions when available
        "active_subscriptions": 0,  # TODO
        "new_signups": 0,  # TODO
        "provider_health": [],
    }


@router.get("/metrics/users")
def metrics_users(range: str = "30d", db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total = db.query(User).count()
    users = db.query(User).limit(100).all()
    result = []
    for u in users:
        try:
            plan = plan_service.get_active_plan(db, u)
            result.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "is_admin": u.is_admin,
                    "is_active": u.is_active,
                    "plan_id": plan.id if plan else None,
                    "plan_name": plan.name if plan else None,
                }
            )
        except Exception:
            result.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "is_admin": u.is_admin,
                    "is_active": u.is_active,
                    "plan_id": None,
                    "plan_name": None,
                }
            )
    return {"range": range, "total": total, "users": result}


@router.get("/metrics/subscriptions")
def metrics_subscriptions(range: str = "30d", admin: User = Depends(get_current_admin)):
    # TODO: implement when subscription data is available
    return {"range": range, "series": [], "by_plan": [], "subscriptions": []}


@router.get("/metrics/searches")
def metrics_searches(range: str = "30d", db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    since = _range_start(range)

    query_expr = func.coalesce(SearchEvent.query_normalized, SearchEvent.query_raw)

    top = (
        db.query(
            query_expr.label("query"),
            func.count().label("count"),
            func.sum(case((SearchEvent.result_count == 0, 1), else_=0)).label("zero_count"),
        )
        .filter(SearchEvent.created_at >= since)
        .group_by(query_expr)
        .order_by(func.count().desc())
        .limit(20)
        .all()
    )
    top_list = [{"query": q or "", "count": cnt or 0, "zero_count": zc or 0} for q, cnt, zc in top]

    zero_queries = (
        db.query(
            query_expr.label("query"),
            func.count().label("count"),
        )
        .filter(SearchEvent.created_at >= since, SearchEvent.result_count == 0)
        .group_by(query_expr)
        .order_by(func.count().desc())
        .limit(20)
        .all()
    )
    zero_list = [{"query": q or "", "count": cnt or 0} for q, cnt in zero_queries]

    bucket = func.date_trunc("day", SearchEvent.created_at)
    series_rows = (
        db.query(
            bucket.label("bucket"),
            func.count().label("searches"),
            func.sum(case((SearchEvent.result_count == 0, 1), else_=0)).label("zero_results"),
            func.sum(case((SearchEvent.status == "error", 1), else_=0)).label("errors"),
        )
        .filter(SearchEvent.created_at >= since)
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )
    series = [
        {
            "bucket": b.isoformat() if b else "",
            "searches": int(s or 0),
            "zero_results": int(z or 0),
            "errors": int(e or 0),
        }
        for b, s, z, e in series_rows
    ]

    providers_sql = text(
        """
        select
          provider,
          count(*) as count,
          sum(case when status = 'error' then 1 else 0 end) as error_count,
          sum(case when cache_hit is true then 1 else 0 end) as cache_hits
        from search_events,
             lateral jsonb_array_elements_text(coalesce(providers, '[]'::jsonb)) as p(provider)
        where created_at >= :since
        group by provider
        order by count desc
        limit 20
        """
    )
    provider_rows = db.execute(providers_sql, {"since": since}).fetchall()
    providers = [
        {
            "provider": row.provider,
            "count": int(row.count or 0),
            "error_count": int(row.error_count or 0),
            "cache_hits": int(row.cache_hits or 0),
        }
        for row in provider_rows
    ]

    return {
        "range": range,
        "top_queries": top_list,
        "zero_queries": zero_list,
        "series": series,
        "providers": providers,
    }


@router.get("/providers/status")
def providers_status(admin: User = Depends(get_current_admin)):
    # TODO: wire to real provider sync status
    return {"providers": []}


@router.get("/providers", response_model=List[ProviderSettingOut])
def list_providers(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    provider_setting_service.ensure_defaults(db)
    settings = provider_setting_service.list_settings(db)
    return settings


@router.patch("/providers/{key}", response_model=ProviderSettingOut)
def update_provider(
    key: str,
    payload: ProviderSettingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if payload.mode and payload.mode not in {"search", "assist", "both"}:
        raise HTTPException(status_code=400, detail="Invalid mode")
    setting = provider_setting_service.update_setting(
        db,
        key=key,
        enabled=payload.enabled,
        priority=payload.priority,
        mode=payload.mode,
    )
    return setting


@router.post("/providers/seed-defaults")
def seed_providers(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    provider_setting_service.ensure_defaults(db)
    return {"seeded": True}


@router.get("/metrics/quota")
def metrics_quota(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since_7d = now - timedelta(days=7)

    def quota_base_query():
        return db.query(SearchEvent).filter(SearchEvent.error_code == "quota_exceeded")

    today_q = quota_base_query().filter(SearchEvent.created_at >= today_start)
    seven_q = quota_base_query().filter(SearchEvent.created_at >= since_7d)

    today_events = today_q.count()
    today_users = today_q.filter(SearchEvent.user_id.isnot(None)).with_entities(func.count(func.distinct(SearchEvent.user_id))).scalar() or 0

    seven_events = seven_q.count()
    seven_users = seven_q.filter(SearchEvent.user_id.isnot(None)).with_entities(func.count(func.distinct(SearchEvent.user_id))).scalar() or 0

    bucket = func.date_trunc("day", SearchEvent.created_at)
    series_rows = (
        db.query(
            bucket.label("bucket"),
            func.count().label("quota_hits"),
            func.count(func.distinct(SearchEvent.user_id)).label("users"),
        )
        .filter(SearchEvent.error_code == "quota_exceeded", SearchEvent.created_at >= since_7d)
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )
    series = [
        {
            "date": b.date().isoformat() if hasattr(b, "date") else b.isoformat(),
            "quota_exceeded_events": int(q or 0),
            "users_hit_quota": int(u or 0),
        }
        for b, q, u in series_rows
    ]

    return {
        "today": {"quota_exceeded_events": today_events, "users_hit_quota": today_users},
        "last_7d": {"quota_exceeded_events": seven_events, "users_hit_quota": seven_users},
        "series_7d": series,
    }


@router.get("/metrics/upgrade-candidates")
def metrics_upgrade_candidates(
    days: int = 7,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    days = max(1, min(days, 60))
    limit = max(1, min(limit, 200))
    since = datetime.utcnow() - timedelta(days=days)

    quota_hits = (
        db.query(
            SearchEvent.user_id.label("user_id"),
            func.count().label("quota_hits"),
            func.max(SearchEvent.created_at).label("last_hit"),
            func.min(SearchEvent.created_at).label("first_hit"),
        )
        .filter(SearchEvent.created_at >= since, SearchEvent.error_code == "quota_exceeded", SearchEvent.user_id.isnot(None))
        .group_by(SearchEvent.user_id)
        .subquery()
    )

    total_searches = (
        db.query(
            SearchEvent.user_id.label("user_id"),
            func.count().label("searches"),
        )
        .filter(SearchEvent.created_at >= since, SearchEvent.user_id.isnot(None))
        .group_by(SearchEvent.user_id)
        .subquery()
    )

    plans = {p.key: {"id": p.id, "name": p.name} for p in db.query(Plan).all()}

    rows = (
        db.query(
            User.id,
            User.email,
            quota_hits.c.quota_hits,
            quota_hits.c.last_hit,
            quota_hits.c.first_hit,
            total_searches.c.searches,
        )
        .join(quota_hits, quota_hits.c.user_id == User.id)
        .outerjoin(total_searches, total_searches.c.user_id == User.id)
        .order_by(quota_hits.c.quota_hits.desc(), quota_hits.c.last_hit.desc())
        .limit(limit)
        .all()
    )

    result = []
    for row in rows:
        active_plan = plan_service.get_active_plan(db, db.get(User, row.id))
        plan_key = active_plan.key if active_plan else "free"
        plan_info = {"id": active_plan.id if active_plan else None, "name": active_plan.name if active_plan else plan_key}
        result.append(
            {
                "user_id": row.id,
                "email": row.email,
                "plan": plan_info,
                "quota_exceeded_count": int(row.quota_hits or 0),
                "total_searches": int(row.searches or 0),
                "last_quota_hit_at": row.last_hit.isoformat() if row.last_hit else None,
                "first_quota_hit_at": row.first_hit.isoformat() if row.first_hit else None,
            }
        )

    return {"range_days": days, "limit": limit, "items": result}


class UserStatusPayload(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: UserStatusPayload,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    prev = user.is_active
    user.is_active = payload.is_active
    db.add(user)
    db.add(
        AdminActionLog(
            admin_user_id=admin.id,
            target_user_id=user.id,
            action="set_status",
            payload_json={"is_active": payload.is_active, "previous": prev},
        )
    )
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "is_active": user.is_active}


class UserPlanPayload(BaseModel):
    plan_id: int


@router.patch("/users/{user_id}/plan")
def update_user_plan(
    user_id: int,
    payload: UserPlanPayload,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    plan = db.get(Plan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=400, detail="Plan not found or inactive")

    plan_service.assign_plan(db, user, plan)
    db.add(
        AdminActionLog(
            admin_user_id=admin.id,
            target_user_id=user.id,
            action="set_plan",
            payload_json={"plan_id": plan.id, "plan_key": plan.key},
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not update plan")
    db.refresh(user)
    return {"id": user.id, "email": user.email, "plan_key": plan.key, "plan_name": plan.name, "plan_id": plan.id}


@router.get("/users/{user_id}/detail")
def admin_user_detail_full(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # plan resolution
    plan = plan_service.get_active_plan(db, user)
    plan_limit = plan.searches_per_day if plan and plan.searches_per_day is not None else None
    if plan_limit is None and plan and plan.key == "free":
        plan_limit = 5
    if plan_limit is None and not plan:
        plan_limit = 5

    usage_today = usage_service.get_or_create_today_usage(db, user.id)
    remaining = None
    if plan_limit is not None:
        remaining = max(plan_limit - usage_today.search_count, 0)
    reset_at = (
        datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if plan_limit is not None
        else None
    )

    since_7d = datetime.utcnow().date() - timedelta(days=6)
    usage_rows = (
        db.query(DailyUsage.usage_date, func.sum(DailyUsage.search_count))
        .filter(DailyUsage.user_id == user.id, DailyUsage.usage_date >= since_7d)
        .group_by(DailyUsage.usage_date)
        .order_by(DailyUsage.usage_date)
        .all()
    )
    usage_series = [{"date": d.isoformat(), "search_count": int(c or 0)} for d, c in usage_rows]

    recent_searches = (
        db.query(SearchEvent)
        .filter(SearchEvent.user_id == user.id)
        .order_by(SearchEvent.created_at.desc())
        .limit(50)
        .all()
    )
    searches_out = [
        {
            "id": s.id,
            "query": s.query_normalized or s.query_raw,
            "result_count": s.result_count,
            "error_code": s.error_code,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in recent_searches
    ]

    action_logs = (
        db.query(AdminActionLog)
        .filter(AdminActionLog.target_user_id == user.id)
        .order_by(desc(AdminActionLog.created_at))
        .limit(50)
        .all()
    )
    actions_out = [
        {
            "action": a.action,
            "payload": a.payload_json,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "admin_user_id": a.admin_user_id,
        }
        for a in action_logs
    ]

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "plan": {"id": plan.id if plan else None, "name": plan.name if plan else plan_key, "searches_per_day": plan_limit},
        "quota": {
            "limit": plan_limit,
            "used": usage_today.search_count,
            "remaining": remaining,
            "reset_at": reset_at.isoformat() if reset_at else None,
        },
        "usage_7d": usage_series,
        "recent_searches": searches_out,
        "admin_actions": actions_out,
    }


@router.get("/users/{user_id}")
def admin_user_detail(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.get(User, user_id)
    if not user:
        return {"error": "not found"}
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin, "is_active": user.is_active}


@router.get("/subscriptions")
def admin_subscriptions(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    # Placeholder until subscriptions table exists
    return {"subscriptions": []}
