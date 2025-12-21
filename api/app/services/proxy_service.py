from datetime import datetime, timedelta
import random
from typing import List, Optional, Tuple
import httpx

from sqlalchemy.orm import Session

from app.models.proxy_endpoint import ProxyEndpoint
from app.services import crypto_service

SENSITIVE_FIELDS = ["password"]

CONNECT_TIMEOUT = 8.0
READ_TIMEOUT = 10.0
OVERALL_TIMEOUT = 20.0


def _encrypt_password(password: Optional[str]) -> Optional[str]:
    if not password:
        return None
    return crypto_service.encrypt_string(password)


def _decrypt_password(enc: Optional[str]) -> Optional[str]:
    if not enc:
        return None
    try:
        return crypto_service.decrypt_string(enc)
    except Exception:
        return None


def mask_username(user: Optional[str]) -> Optional[str]:
    if not user:
        return None
    return user[:4] + "***"


# CRUD

def list_proxies(db: Session) -> List[ProxyEndpoint]:
    return db.query(ProxyEndpoint).order_by(ProxyEndpoint.created_at.desc()).all()


def list_enabled_proxies(db: Session) -> List[ProxyEndpoint]:
    return db.query(ProxyEndpoint).filter(ProxyEndpoint.is_enabled.is_(True)).order_by(ProxyEndpoint.name).all()


def get_proxy(db: Session, proxy_id: int) -> Optional[ProxyEndpoint]:
    return db.get(ProxyEndpoint, proxy_id)


def create_proxy(db: Session, payload: dict) -> ProxyEndpoint:
    data = payload.copy()
    if "password" in data:
        data["password_encrypted"] = _encrypt_password(data.pop("password"))
    proxy = ProxyEndpoint(**data)
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


def update_proxy(db: Session, proxy_id: int, payload: dict) -> Optional[ProxyEndpoint]:
    proxy = get_proxy(db, proxy_id)
    if not proxy:
        return None
    data = payload.copy()
    if "password" in data:
        proxy.password_encrypted = _encrypt_password(data.pop("password"))
    for field, value in data.items():
        setattr(proxy, field, value)
    proxy.updated_at = datetime.utcnow()
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


# Health check

def check_proxy(db: Session, proxy: ProxyEndpoint) -> dict:
    proxy_url = build_proxy_url(proxy)
    result = {"ok": False, "stage": "proxy_check", "error_code": None}
    try:
        timeout = httpx.Timeout(OVERALL_TIMEOUT, connect=CONNECT_TIMEOUT, read=READ_TIMEOUT, write=READ_TIMEOUT)
        with httpx.Client(proxy=proxy_url, timeout=timeout, verify=False) as client:
            start = datetime.utcnow()
            resp = client.get("https://api.ipify.org", params={"format": "json"})
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            result.update({
                "ok": resp.status_code == 200,
                "status_code": resp.status_code,
                "body_len": len(resp.text or ""),
                "exit_ip": resp.json().get("ip") if resp.headers.get("content-type", "").startswith("application/json") else None,
                "elapsed_ms": int(elapsed),
            })
    except httpx.ConnectTimeout:
        result["error"] = "Proxy connect timeout"
        result["error_code"] = "PROXY_CONNECT_TIMEOUT"
    except httpx.ReadTimeout:
        result["error"] = "Proxy SSL/handshake timeout"
        result["error_code"] = "PROXY_SSL_HANDSHAKE_TIMEOUT"
    except httpx.ProxyError as e:
        msg = str(e)
        result["error"] = msg
        if "403" in msg or "auth" in msg.lower():
            result["error_code"] = "PROXY_AUTH_FAILED"
    except Exception as e:
        result["error"] = str(e)

    # Update health tracking
    proxy.last_check_at = datetime.utcnow()
    proxy.last_check_status = "ok" if result.get("ok") else "failed"
    proxy.last_exit_ip = result.get("exit_ip")
    proxy.last_error = result.get("error")

    if result.get("ok"):
        # Success: reset health counters
        proxy.consecutive_failures = 0
        proxy.unhealthy_until = None
        proxy.last_failure_at = None
    else:
        # Failure: increment counter and apply banning logic
        proxy.consecutive_failures = (proxy.consecutive_failures or 0) + 1
        proxy.last_failure_at = datetime.utcnow()
        proxy.unhealthy_until = datetime.utcnow() + timedelta(minutes=5)

        # Ban proxy if failures exceed threshold
        if proxy.consecutive_failures >= 3:
            # Ban for 30 minutes after 3 consecutive failures
            proxy.banned_until = datetime.utcnow() + timedelta(minutes=30)

    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return result


def check_all(db: Session) -> List[dict]:
    outputs = []
    for proxy in db.query(ProxyEndpoint).filter(ProxyEndpoint.is_enabled.is_(True)).all():
        outputs.append({"id": proxy.id, **check_proxy(db, proxy)})
    return outputs


# Selection

def build_proxy_url(proxy: ProxyEndpoint) -> str:
    user = proxy.username or ""
    pwd = _decrypt_password(proxy.password_encrypted) or ""
    if user and pwd:
        return f"{proxy.scheme}://{user}:{pwd}@{proxy.host}:{proxy.port}"
    return f"{proxy.scheme}://{proxy.host}:{proxy.port}"


def select_proxy_for_run(db: Session) -> Optional[ProxyEndpoint]:
    now = datetime.utcnow()
    enabled = db.query(ProxyEndpoint).filter(
        ProxyEndpoint.is_enabled.is_(True),
        (ProxyEndpoint.unhealthy_until.is_(None) | (ProxyEndpoint.unhealthy_until <= now)),
        (ProxyEndpoint.banned_until.is_(None) | (ProxyEndpoint.banned_until <= now))  # Exclude banned proxies
    ).all()
    if not enabled:
        return None

    ok_recent = []
    stale_or_unknown = []
    now = datetime.utcnow()
    for p in enabled:
        if p.last_check_status == "ok" and p.last_check_at and (now - p.last_check_at) <= timedelta(minutes=30):
            ok_recent.append(p)
        else:
            stale_or_unknown.append(p)

    def expand(pool):
        expanded = []
        for p in pool:
            expanded.extend([p] * max(1, p.weight))
        return expanded

    pool = expand(ok_recent) if ok_recent else expand(stale_or_unknown)
    if not pool:
        return None
    return random.choice(pool)


def record_proxy_failure(db: Session, proxy: ProxyEndpoint, error: str) -> None:
    """Record a proxy failure and apply banning logic if threshold exceeded."""
    now = datetime.utcnow()
    proxy.last_check_at = now
    proxy.last_check_status = "failed"
    proxy.last_error = error[:500]
    proxy.last_failure_at = now

    # Increment consecutive failures
    proxy.consecutive_failures = (proxy.consecutive_failures or 0) + 1

    # Set temporary unhealthy period
    proxy.unhealthy_until = now + timedelta(minutes=5)

    # Ban proxy if failures exceed threshold
    if proxy.consecutive_failures >= 3:
        # Ban for 30 minutes after 3 consecutive failures
        proxy.banned_until = now + timedelta(minutes=30)

    db.add(proxy)
    db.commit()


def ban_proxy(db: Session, proxy_id: int, duration_minutes: int = 60) -> Optional[ProxyEndpoint]:
    """Manually ban a proxy for a specified duration."""
    proxy = get_proxy(db, proxy_id)
    if not proxy:
        return None

    proxy.banned_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    proxy.consecutive_failures = 3  # Mark as if it failed threshold
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


def unban_proxy(db: Session, proxy_id: int) -> Optional[ProxyEndpoint]:
    """Manually unban a proxy and reset health counters."""
    proxy = get_proxy(db, proxy_id)
    if not proxy:
        return None

    proxy.banned_until = None
    proxy.consecutive_failures = 0
    proxy.unhealthy_until = None
    proxy.last_failure_at = None
    proxy.last_check_status = None
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


def mask_proxy(proxy: ProxyEndpoint) -> dict:
    return {
        "id": proxy.id,
        "name": proxy.name,
        "host": proxy.host,
        "port": proxy.port,
        "username": mask_username(proxy.username),
        "scheme": proxy.scheme,
        "is_enabled": proxy.is_enabled,
        "weight": proxy.weight,
        "max_concurrency": proxy.max_concurrency,
        "region": proxy.region,
        "last_check_at": proxy.last_check_at,
        "last_check_status": proxy.last_check_status,
        "last_exit_ip": proxy.last_exit_ip,
        "last_error": proxy.last_error,
        "consecutive_failures": proxy.consecutive_failures,
        "banned_until": proxy.banned_until,
        "last_failure_at": proxy.last_failure_at,
        "unhealthy_until": proxy.unhealthy_until,
        "created_at": proxy.created_at,
        "updated_at": proxy.updated_at,
    }
