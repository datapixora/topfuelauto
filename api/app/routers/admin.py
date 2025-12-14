from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text, case
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.search_event import SearchEvent
from app.models.user import User
from app.models.broker_lead import BrokerLead
from app.models.listing import Listing
from app.models.plan import Plan
from app.models.admin_action_log import AdminActionLog
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

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
    return {
        "range": range,
        "total": total,
        "users": [
            {"id": u.id, "email": u.email, "is_pro": u.is_pro, "is_admin": u.is_admin, "is_active": u.is_active}
            for u in users
        ],
    }


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
            User.is_pro,
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
        plan_key = "pro" if row.is_pro else "free"
        plan_info = plans.get(plan_key, {"id": None, "name": plan_key})
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

    user.is_pro = plan.key == "pro"
    db.add(user)
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
    return {"id": user.id, "email": user.email, "is_pro": user.is_pro, "plan_key": plan.key, "plan_name": plan.name}


@router.get("/users/{user_id}")
def admin_user_detail(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.get(User, user_id)
    if not user:
        return {"error": "not found"}
    return {"id": user.id, "email": user.email, "is_pro": user.is_pro, "is_admin": user.is_admin, "is_active": user.is_active}


@router.get("/subscriptions")
def admin_subscriptions(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    # Placeholder until subscriptions table exists
    return {"subscriptions": []}
