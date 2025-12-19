"""Admin database diagnostics (locks and blockers)."""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/db", tags=["admin-db"])


class TerminateBlockersResponse(BaseModel):
    ok: bool
    terminated_pids: List[int]
    skipped_pids: List[int]
    details: Dict[str, Any]


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


@router.post("/locks/proxies/terminate-blockers", response_model=TerminateBlockersResponse)
def terminate_proxies_blockers(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> TerminateBlockersResponse:
    """
    Safely terminate sessions blocking locks on the 'proxies' table.

    Safety rules:
    - Only terminate PIDs that are CONFIRMED blockers of locks on relation 'proxies'
    - Do not terminate the current session
    - Do not terminate system users (postgres, rdsadmin, etc.)
    - Prefer terminating sessions that are 'idle in transaction' or have long xact_age
    """

    # Get current session PID
    current_pid_result = db.execute(text("SELECT pg_backend_pid()")).fetchone()
    current_pid = current_pid_result[0] if current_pid_result else None

    logger.info("terminate_proxies_blockers called", extra={
        "current_pid": current_pid,
        "admin_user_id": admin.id
    })

    # Find blockers for the proxies table
    # This query identifies processes blocking locks on the proxies table
    blockers_query = text("""
        WITH proxies_locks AS (
            SELECT l.pid, l.mode, l.granted
            FROM pg_locks l
            JOIN pg_class c ON c.oid = l.relation
            WHERE c.relname = 'proxies'
        ),
        blocking_relationships AS (
            SELECT
                bl.pid AS blocked_pid,
                kl.pid AS blocking_pid
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
                AND bl.relation IN (SELECT oid FROM pg_class WHERE relname = 'proxies')
        )
        SELECT DISTINCT
            br.blocking_pid AS pid,
            a.usename,
            a.application_name,
            a.state,
            a.query_start,
            a.xact_start,
            NOW() - a.xact_start AS xact_age,
            a.query
        FROM blocking_relationships br
        JOIN pg_stat_activity a ON a.pid = br.blocking_pid
        WHERE a.pid IS NOT NULL
        ORDER BY a.xact_start NULLS LAST;
    """)

    blockers_result = db.execute(blockers_query).fetchall()

    if not blockers_result:
        logger.info("No blockers found for proxies table")
        return TerminateBlockersResponse(
            ok=True,
            terminated_pids=[],
            skipped_pids=[],
            details={"message": "No blockers found"}
        )

    terminated_pids: List[int] = []
    skipped_pids: List[int] = []
    skip_reasons: Dict[int, str] = {}

    # System users that should never be terminated
    system_users = {'postgres', 'rdsadmin', 'rds_superuser', 'rds_replication'}

    for row in blockers_result:
        pid = row[0]
        usename = row[1]
        state = row[3]

        # Safety checks
        if pid == current_pid:
            skipped_pids.append(pid)
            skip_reasons[pid] = "current_session"
            logger.warning(f"Skipping PID {pid}: current session")
            continue

        if usename and usename.lower() in system_users:
            skipped_pids.append(pid)
            skip_reasons[pid] = "system_user"
            logger.warning(f"Skipping PID {pid}: system user {usename}")
            continue

        # Attempt to terminate
        try:
            # Try pg_terminate_backend (sends SIGTERM)
            terminate_result = db.execute(
                text("SELECT pg_terminate_backend(:pid)"),
                {"pid": pid}
            ).fetchone()

            if terminate_result and terminate_result[0]:
                terminated_pids.append(pid)
                logger.info(f"Terminated PID {pid}", extra={
                    "pid": pid,
                    "usename": usename,
                    "state": state
                })
            else:
                # If terminate failed, try cancel as fallback
                cancel_result = db.execute(
                    text("SELECT pg_cancel_backend(:pid)"),
                    {"pid": pid}
                ).fetchone()

                if cancel_result and cancel_result[0]:
                    terminated_pids.append(pid)
                    logger.info(f"Cancelled PID {pid}", extra={
                        "pid": pid,
                        "usename": usename,
                        "state": state
                    })
                else:
                    skipped_pids.append(pid)
                    skip_reasons[pid] = "terminate_failed"
                    logger.error(f"Failed to terminate or cancel PID {pid}")

        except Exception as e:
            skipped_pids.append(pid)
            skip_reasons[pid] = f"error: {str(e)}"
            logger.exception(f"Error terminating PID {pid}", extra={"pid": pid, "error": str(e)})

    db.commit()

    logger.info("terminate_proxies_blockers completed", extra={
        "terminated_count": len(terminated_pids),
        "skipped_count": len(skipped_pids),
        "terminated_pids": terminated_pids,
        "skipped_pids": skipped_pids
    })

    return TerminateBlockersResponse(
        ok=True,
        terminated_pids=terminated_pids,
        skipped_pids=skipped_pids,
        details={
            "blockers_found": len(blockers_result),
            "skip_reasons": skip_reasons
        }
    )

