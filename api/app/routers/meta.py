"""
Meta endpoint for release tracking and deployment verification.
"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("")
async def get_meta():
    """
    Get release metadata for deployment verification.

    Returns:
        - git_sha: Git commit SHA (from GIT_SHA env var)
        - build_time: Build timestamp (from BUILD_TIME env var)

    Usage:
        curl https://api.topfuelauto.com/api/v1/meta

    This endpoint helps verify that the expected commit is deployed to production.
    """
    settings = get_settings()
    return {
        "git_sha": settings.git_sha or "unknown",
        "build_time": settings.build_time or "unknown",
    }
