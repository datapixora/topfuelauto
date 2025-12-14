import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User

logger = logging.getLogger(__name__)


def create_user(db: Session, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(email=email, password_hash=get_password_hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_token_for_user(user: User) -> str:
    return create_access_token({"sub": str(user.id)})


def authenticate_user(db: Session, email: str, password: str) -> str:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.info("Login failed: user not found", extra={"email": email})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not user.password_hash:
        logger.warning("Login failed: missing password hash", extra={"user_id": user.id})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    try:
        valid = verify_password(password, user.password_hash)
    except Exception:
        logger.exception("Password verification error", extra={"user_id": user.id})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not valid:
        logger.info("Login failed: bad password", extra={"user_id": user.id})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id)})
    return token
