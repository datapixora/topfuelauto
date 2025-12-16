from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.schemas import proxy as schemas
from app.services import proxy_service
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin/proxies", tags=["admin-proxies"])


@router.get("/", response_model=list[schemas.ProxyOut])
def list_proxies(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    proxies = proxy_service.list_proxies(db)
    return [proxy_service.mask_proxy(p) for p in proxies]


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
