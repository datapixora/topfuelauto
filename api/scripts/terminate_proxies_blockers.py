#!/usr/bin/env python3
"""
Emergency CLI script to terminate sessions blocking locks on the 'proxies' table.

Usage:
    python api/scripts/terminate_proxies_blockers.py

Environment:
    DATABASE_URL - PostgreSQL connection string (required)

Exit codes:
    0 - Success (no blockers found or all successfully terminated)
    1 - Error (failed to terminate some blockers or database error)
"""

import logging
import os
import sys
from typing import List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get DATABASE_URL from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    return database_url


def create_session(database_url: str) -> Session:
    """Create a database session."""
    engine = create_engine(database_url, future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return SessionLocal()


def find_proxies_blockers(db: Session) -> List[tuple]:
    """Find sessions blocking locks on the 'proxies' table."""

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

    return db.execute(blockers_query).fetchall()


def terminate_blockers(db: Session) -> Dict[str, Any]:
    """
    Terminate sessions blocking locks on the 'proxies' table.

    Returns:
        Dictionary with termination results
    """

    # Get current session PID
    current_pid_result = db.execute(text("SELECT pg_backend_pid()")).fetchone()
    current_pid = current_pid_result[0] if current_pid_result else None

    logger.info(f"Current session PID: {current_pid}")

    # Find blockers
    blockers = find_proxies_blockers(db)

    if not blockers:
        logger.info("No blockers found for proxies table")
        return {
            "ok": True,
            "blockers_found": 0,
            "terminated_pids": [],
            "skipped_pids": []
        }

    logger.info(f"Found {len(blockers)} blocking session(s)")

    # Print blocker details
    for row in blockers:
        pid, usename, app_name, state, query_start, xact_start, xact_age, query = row
        logger.info(f"  PID {pid}: user={usename}, state={state}, xact_age={xact_age}, app={app_name}")
        if query:
            query_preview = query[:100] + "..." if len(query) > 100 else query
            logger.info(f"    Query: {query_preview}")

    terminated_pids: List[int] = []
    skipped_pids: List[int] = []
    skip_reasons: Dict[int, str] = {}

    # System users that should never be terminated
    system_users = {'postgres', 'rdsadmin', 'rds_superuser', 'rds_replication'}

    for row in blockers:
        pid = row[0]
        usename = row[1]
        state = row[3]

        # Safety checks
        if pid == current_pid:
            skipped_pids.append(pid)
            skip_reasons[pid] = "current_session"
            logger.warning(f"Skipping PID {pid}: current session (cannot terminate self)")
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
                logger.info(f"✓ Terminated PID {pid} (user={usename}, state={state})")
            else:
                # If terminate failed, try cancel as fallback
                cancel_result = db.execute(
                    text("SELECT pg_cancel_backend(:pid)"),
                    {"pid": pid}
                ).fetchone()

                if cancel_result and cancel_result[0]:
                    terminated_pids.append(pid)
                    logger.info(f"✓ Cancelled PID {pid} (user={usename}, state={state})")
                else:
                    skipped_pids.append(pid)
                    skip_reasons[pid] = "terminate_failed"
                    logger.error(f"✗ Failed to terminate or cancel PID {pid}")

        except Exception as e:
            skipped_pids.append(pid)
            skip_reasons[pid] = f"error: {str(e)}"
            logger.exception(f"✗ Error terminating PID {pid}: {e}")

    db.commit()

    return {
        "ok": len(skipped_pids) == 0,
        "blockers_found": len(blockers),
        "terminated_pids": terminated_pids,
        "skipped_pids": skipped_pids,
        "skip_reasons": skip_reasons
    }


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Proxies Table Blocker Termination Script")
    logger.info("=" * 60)

    database_url = get_database_url()

    db = None
    try:
        db = create_session(database_url)
        result = terminate_blockers(db)

        logger.info("=" * 60)
        logger.info("Summary:")
        logger.info(f"  Blockers found: {result['blockers_found']}")
        logger.info(f"  Terminated: {len(result['terminated_pids'])}")
        logger.info(f"  Skipped: {len(result['skipped_pids'])}")

        if result['terminated_pids']:
            logger.info(f"  Terminated PIDs: {result['terminated_pids']}")

        if result['skipped_pids']:
            logger.warning(f"  Skipped PIDs: {result['skipped_pids']}")
            for pid, reason in result.get('skip_reasons', {}).items():
                logger.warning(f"    PID {pid}: {reason}")

        logger.info("=" * 60)

        # Exit with appropriate code
        if result['ok']:
            logger.info("✓ Success: All blockers cleared")
            sys.exit(0)
        else:
            logger.error("✗ Warning: Some blockers could not be terminated")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
