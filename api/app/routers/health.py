import os
from datetime import datetime, timezone

from fastapi import APIRouter

# Versioned health endpoint
router = APIRouter(prefix="/api/v1", tags=["health"])


def get_health_payload():
    """Lightweight health payload without touching external deps."""
    version = os.getenv("APP_VERSION") or os.getenv("GIT_SHA") or "unknown"
    return {
        "ok": True,
        "service": "api",
        "ts": datetime.now(timezone.utc).isoformat(),
        "version": version,
    }


@router.get("/health")
async def health_check():
    """Primary versioned health endpoint for web checks."""
    return get_health_payload()
