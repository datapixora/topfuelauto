from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text, case
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.search_event import SearchEvent
from app.models.user import User
from app.models.broker_lead import BrokerLead
from app.models.listing import Listing

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
    return {"range": range, "total": total, "users": [{"id": u.id, "email": u.email, "is_pro": u.is_pro, "is_admin": u.is_admin} for u in users]}


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


@router.get("/users/{user_id}")
def admin_user_detail(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.get(User, user_id)
    if not user:
        return {"error": "not found"}
    return {"id": user.id, "email": user.email, "is_pro": user.is_pro, "is_admin": user.is_admin}


@router.get("/subscriptions")
def admin_subscriptions(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    # Placeholder until subscriptions table exists
    return {"subscriptions": []}
