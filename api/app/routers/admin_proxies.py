from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.core.security import get_current_admin
from app.schemas import proxy as schemas
from app.schemas.data_engine import ProxyOption
from app.services import proxy_service
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin/proxies", tags=["admin-proxies"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[schemas.ProxyOut])
def list_proxies(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    proxies = proxy_service.list_proxies(db)
    return [proxy_service.mask_proxy(p) for p in proxies]


@router.get("/options", response_model=list[ProxyOption])
def get_proxy_options(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Get list of enabled proxies for source configuration (no secrets)"""
    proxies = proxy_service.list_enabled_proxies(db)
    return [
        ProxyOption(
            id=p.id,
            name=p.name,
            host=p.host,
            port=p.port,
            scheme=p.scheme,
            last_check_status=p.last_check_status,
            last_exit_ip=p.last_exit_ip,
        )
        for p in proxies
    ]


@router.post("/", response_model=schemas.ProxyOut, status_code=201)
def create_proxy(payload: schemas.ProxyCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    data = payload.dict()
    proxy = proxy_service.create_proxy(db, data)
    return proxy_service.mask_proxy(proxy)


@router.patch("/{proxy_id}", response_model=schemas.ProxyOut)
def update_proxy(proxy_id: int, payload: schemas.ProxyUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    data = payload.dict(exclude_unset=True)
    proxy = proxy_service.update_proxy(db, proxy_id, data)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return proxy_service.mask_proxy(proxy)


@router.post("/{proxy_id}/check")
def check_proxy(proxy_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    proxy = proxy_service.get_proxy(db, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    result = proxy_service.check_proxy(db, proxy)
    return {"id": proxy.id, **result}


@router.post("/check-bulk")
def check_bulk(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return proxy_service.check_all(db)


@router.post("/refresh-smartproxy")
def refresh_smartproxy_pool(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Refresh proxy pool from Smartproxy API.

    Fetches all available proxies from Smartproxy and syncs them to database.
    Creates new proxies or updates existing ones.

    Returns:
        Sync statistics: created, updated, total

    Raises:
        HTTPException: If Smartproxy API is not configured or request fails
    """
    try:
        from app.services.smartproxy_service import SmartproxyAPI, sync_smartproxy_to_db

        # Fetch proxies from Smartproxy API
        api = SmartproxyAPI()
        proxies = api.fetch_proxies()

        # Sync to database
        stats = sync_smartproxy_to_db(db, proxies)

        logger.info(f"Admin {admin.email} refreshed Smartproxy pool: {stats}")
        return {
            "success": True,
            "message": f"Synced {stats['total']} proxies from Smartproxy",
            **stats,
        }

    except ValueError as e:
        logger.error(f"Smartproxy configuration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to refresh Smartproxy pool: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Smartproxy API error: {str(e)}")


@router.post("/{proxy_id}/ban")
def ban_proxy(
    proxy_id: int,
    duration_minutes: int = 60,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Manually ban a proxy for specified duration.

    Args:
        proxy_id: ID of proxy to ban
        duration_minutes: Ban duration in minutes (default: 60)

    Returns:
        Updated proxy object

    Raises:
        HTTPException: If proxy not found
    """
    proxy = proxy_service.ban_proxy(db, proxy_id, duration_minutes)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    logger.info(f"Admin {admin.email} banned proxy {proxy_id} for {duration_minutes} minutes")
    return proxy_service.mask_proxy(proxy)


@router.post("/{proxy_id}/unban")
def unban_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Manually unban a proxy and reset health counters.

    Args:
        proxy_id: ID of proxy to unban

    Returns:
        Updated proxy object

    Raises:
        HTTPException: If proxy not found
    """
    proxy = proxy_service.unban_proxy(db, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    logger.info(f"Admin {admin.email} unbanned proxy {proxy_id}")
    return proxy_service.mask_proxy(proxy)
