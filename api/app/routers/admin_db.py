"""Admin database diagnostics (locks and blockers)."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin/db", tags=["admin-db"])


@router.get("/locks/proxies")
def get_proxy_locks(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Return sessions/locks/blockers related to the `proxies` table for debugging DDL locks."""

    activity_sql = text(
        """
        SELECT pid,
               usename,
               application_name,
               client_addr,
               state,
               wait_event_type,
               wait_event,
               query_start,
               NOW() - query_start AS query_age,
               xact_start,
               NOW() - xact_start AS xact_age,
               query
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND (query ILIKE '%proxies%' OR relid IN (SELECT oid FROM pg_class WHERE relname='proxies'))
        ORDER BY xact_start NULLS LAST;
        """
    )

    locks_sql = text(
        """
        SELECT l.pid,
               a.usename,
               a.application_name,
               a.state,
               a.wait_event_type,
               a.wait_event,
               a.query_start,
               NOW() - a.query_start AS query_age,
               l.mode,
               l.granted,
               a.query
        FROM pg_locks l
        JOIN pg_class c ON c.oid = l.relation
        JOIN pg_stat_activity a ON a.pid = l.pid
        WHERE c.relname = 'proxies'
        ORDER BY l.granted DESC, a.query_start;
        """
    )

    blockers_sql = text(
        """
        WITH blocked AS (
          SELECT bl.pid AS blocked_pid, kl.pid AS blocking_pid
          FROM pg_locks bl
          JOIN pg_locks kl
            ON bl.locktype = kl.locktype
           AND bl.database IS NOT DISTINCT FROM kl.database
           AND bl.relation IS NOT DISTINCT FROM kl.relation
           AND bl.page IS NOT DISTINCT FROM kl.page
           AND bl.tuple IS NOT DISTINCT FROM kl.tuple
           AND bl.virtualxid IS NOT DISTINCT FROM kl.virtualxid
           AND bl.transactionid IS NOT DISTINCT FROM kl.transactionid
           AND bl.classid IS NOT DISTINCT FROM kl.classid
           AND bl.objid IS NOT DISTINCT FROM kl.objid
           AND bl.objsubid IS NOT DISTINCT FROM kl.objsubid
          WHERE NOT bl.granted AND kl.granted
        )
        SELECT b.blocked_pid,
               a.query AS blocked_query,
               b.blocking_pid,
               a2.query AS blocking_query
        FROM blocked b
        LEFT JOIN pg_stat_activity a ON a.pid = b.blocked_pid
        LEFT JOIN pg_stat_activity a2 ON a2.pid = b.blocking_pid;
        """
    )

    def rows_to_dicts(result):
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]

    activity = rows_to_dicts(db.execute(activity_sql))
    locks = rows_to_dicts(db.execute(locks_sql))
    blockers = rows_to_dicts(db.execute(blockers_sql))

    return {
        "activity": activity,
        "locks": locks,
        "blockers": blockers,
    }

