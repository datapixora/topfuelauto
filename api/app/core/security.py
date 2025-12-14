import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError, JWTClaimsError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _log_backend():
    try:
        handler = pwd_context.handler("bcrypt")
        backend = getattr(handler, "backend", None)
        logger.info("passlib bcrypt backend loaded", extra={"backend": str(backend)})
    except Exception:
        logger.exception("Could not introspect passlib bcrypt backend")


_log_backend()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    exp_seconds = settings.token_expires_seconds or settings.access_token_expire_minutes * 60
    expire = datetime.utcnow() + (expires_delta or timedelta(seconds=exp_seconds))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.algorithm])
        return payload
    except ExpiredSignatureError:
        logger.info("JWT verification failed", extra={"reason": "expired"})
    except JWTClaimsError:
        logger.info("JWT verification failed", extra={"reason": "invalid_payload"})
    except JWTError:
        logger.info("JWT verification failed", extra={"reason": "invalid_signature"})
    except Exception:
        logger.exception("JWT verification failed", extra={"reason": "unknown"})
    return None


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        logger.info("JWT verification failed", extra={"reason": "missing_or_invalid"})
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        logger.info("JWT verification failed", extra={"reason": "missing_sub"})
        raise credentials_exception
    user = db.get(User, int(user_id))
    if user is None:
        logger.info("JWT verification failed", extra={"reason": "user_not_found"})
        raise credentials_exception
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def get_optional_user(db: Session = Depends(get_db), token: str | None = Depends(optional_oauth2_scheme)) -> User | None:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.get(User, int(user_id))
