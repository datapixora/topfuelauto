from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import auth as auth_schema
from app.services import auth_service
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", response_model=auth_schema.UserOut)
def signup(payload: auth_schema.UserCreate, db: Session = Depends(get_db)):
    user = auth_service.create_user(db, payload.email, payload.password)
    return user


@router.post("/login", response_model=auth_schema.Token)
def login(payload: auth_schema.UserLogin, db: Session = Depends(get_db)):
    token = auth_service.authenticate_user(db, payload.email, payload.password)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=auth_schema.UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user