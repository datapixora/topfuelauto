"""Admin API endpoints for site settings."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.services import settings_service
import logging

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin", "settings"])
logger = logging.getLogger(__name__)


class SettingUpdate(BaseModel):
    value: Optional[str]
    description: Optional[str] = None


@router.get("/bidfax-cookies")
def get_bidfax_cookies(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get default Bidfax cookies for automatic injection."""
    cookies = settings_service.get_setting(db, "bidfax_cookies")
    return {
        "cookies": cookies,
        "has_cookies": bool(cookies),
        "info": "These cookies will be automatically injected in browser mode if no cookies are explicitly provided."
    }


@router.put("/bidfax-cookies")
def update_bidfax_cookies(
    payload: SettingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update default Bidfax cookies.
    
    These cookies will be automatically injected when using browser mode,
    allowing bypass of Cloudflare challenges without manual input.
    
    To get cookies:
    1. Open https://en.bidfax.info in your browser
    2. Open DevTools (F12) -> Application -> Cookies
    3. Copy all cookies, especially cf_clearance
    4. Format: "cf_clearance=xxx; _ga=xxx; PHPSESSID=xxx"
    """
    setting = settings_service.set_setting(
        db,
        "bidfax_cookies",
        payload.value,
        payload.description or "Default cookies for Bidfax browser automation"
    )
    
    logger.info(f"Admin {admin.email} updated default Bidfax cookies")
    
    return {
        "success": True,
        "message": "Default cookies updated successfully",
        "has_cookies": bool(setting.value)
    }


@router.delete("/bidfax-cookies")
def delete_bidfax_cookies(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Clear default Bidfax cookies."""
    deleted = settings_service.delete_setting(db, "bidfax_cookies")
    
    if deleted:
        logger.info(f"Admin {admin.email} deleted default Bidfax cookies")
        return {"success": True, "message": "Default cookies cleared"}
    
    return {"success": False, "message": "No cookies to delete"}
