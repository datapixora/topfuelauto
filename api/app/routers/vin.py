from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services import vin_service
from app.schemas import vin as vin_schema

router = APIRouter(prefix="/api/v1/vin", tags=["vin"])


@router.get("/decode", response_model=vin_schema.VinDecodeResponse)
def decode_vin(vin: str, db: Session = Depends(get_db)):
    result = vin_service.decode_vin(db, vin)
    return result


@router.get("/history", response_model=vin_schema.VinHistoryResponse)
def vin_history(vin: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Pro subscription required")
    result = vin_service.history_vin(db, vin)
    return result