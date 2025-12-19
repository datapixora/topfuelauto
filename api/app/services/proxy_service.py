from datetime import datetime, timedelta
import logging
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
IPIFY_HTTP = "http://api.ipify.org?format=json"
IPIFY_HTTPS = "https://api.ipify.org?format=json"

logger = logging.getLogger(__name__)


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

def _map_proxy_error(stage: str, exc: Exception) -> Tuple[str, str]:
    """
    Map httpx exception to normalized proxy error_code and message.
    """
    msg = str(exc)
    lower = msg.lower()
    code = None

    if isinstance(exc, httpx.ConnectTimeout):
        code = "PROXY_CONNECT_TIMEOUT"
    elif isinstance(exc, httpx.ReadTimeout):
        # Treat read timeout during CONNECT/TLS as handshake timeout
        code = "PROXY_SSL_HANDSHAKE_TIMEOUT"
    elif isinstance(exc, httpx.ProxyError):
        if "unexpected eof" in lower or "eof occurred" in lower:
            code = "PROXY_TLS_EOF" if stage == "proxy_check_https" else "PROXY_EOF"
        elif "auth" in lower or "forbidden" in lower or "407" in lower:
            code = "PROXY_AUTH_FAILED"
        elif "dns" in lower or "getaddrinfo" in lower or "name or service" in lower:
            code = "PROXY_DNS_FAILED"
    elif isinstance(exc, httpx.ConnectError):
        if "dns" in lower or "getaddrinfo" in lower or "name or service" in lower:
            code = "PROXY_DNS_FAILED"
    # Generic EOF detector (covers ssl.SSLError path)
    if not code and ("unexpected eof" in lower or "eof occurred" in lower):
        code = "PROXY_TLS_EOF" if stage == "proxy_check_https" else "PROXY_EOF"
    if not code and ("auth" in lower or "forbidden" in lower or "407" in lower):
        code = "PROXY_AUTH_FAILED"
    if not code and ("dns" in lower or "getaddrinfo" in lower or "name or service" in lower):
        code = "PROXY_DNS_FAILED"

    return code or "PROXY_ERROR", msg


def _probe_proxy_stage(proxy_url: str, target_url: str, stage: str) -> Tuple[dict, Optional[str], Optional[str]]:
    """
    Execute a lightweight request through the proxy for the given stage.
    Returns probe result + (error_code, error_message).
    """
    start = datetime.utcnow()
    timeout = httpx.Timeout(OVERALL_TIMEOUT, connect=CONNECT_TIMEOUT, read=READ_TIMEOUT, write=READ_TIMEOUT)
    try:
        with httpx.Client(proxy=proxy_url, timeout=timeout, verify=False) as client:
            resp = client.get(target_url)
            latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
            content_type = resp.headers.get("content-type", "").lower()
            exit_ip = None
            if resp.status_code == 200:
                if "application/json" in content_type:
                    try:
                        exit_ip = resp.json().get("ip")
                    except Exception:
                        exit_ip = None
                else:
                    exit_ip = (resp.text or "").strip()
            probe = {
                "ok": resp.status_code == 200,
                "status_code": resp.status_code,
                "body_len": len(resp.text or ""),
                "exit_ip": exit_ip,
                "latency_ms": latency_ms,
                "url": target_url,
            }
            if not probe["ok"]:
                return probe, "PROXY_HTTP_STATUS", f"Unexpected status {resp.status_code}"
            return probe, None, None
    except Exception as exc:  # noqa: BLE001 - we map to structured codes
        latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        code, message = _map_proxy_error(stage, exc)
        return (
            {
                "ok": False,
                "status_code": None,
                "body_len": 0,
                "exit_ip": None,
                "latency_ms": latency_ms,
                "url": target_url,
                "error": str(exc),
            },
            code,
            message,
        )


def check_proxy(db: Session, proxy: ProxyEndpoint) -> dict:
    proxy_url = build_proxy_url(proxy)
    result = {
        "ok": False,
        "stage": "proxy_check_http",
        "error_code": None,
        "exit_ip": None,
        "proxy": {
            "id": proxy.id,
            "name": proxy.name,
            "host": proxy.host,
            "port": proxy.port,
            "scheme": proxy.scheme,
        },
        "http": None,
        "https": None,
        "error": None,
        "debug": {
            "proxy_url": f"{proxy.scheme}://{proxy.host}:{proxy.port}",
        },
    }

    def _persist(outcome: dict) -> dict:
        proxy.last_check_at = datetime.utcnow()
        proxy.last_check_status = "ok" if outcome.get("ok") else "failed"
        proxy.last_exit_ip = outcome.get("exit_ip")
        proxy.last_error = None
        if not outcome.get("ok"):
            proxy.unhealthy_until = datetime.utcnow() + timedelta(minutes=5)
            err_obj = outcome.get("error") or {}
            if isinstance(err_obj, dict):
                proxy.last_error = err_obj.get("message")
            else:
                proxy.last_error = str(err_obj) if err_obj else None
            if not proxy.last_error:
                proxy.last_error = outcome.get("error_code") or outcome.get("http", {}).get("error") or None
        db.add(proxy)
        db.commit()
        db.refresh(proxy)
        return outcome

    # Stage 1: plain HTTP (no TLS) to confirm basic CONNECT/forwarding
    http_probe, http_code, http_msg = _probe_proxy_stage(proxy_url, IPIFY_HTTP, "proxy_check_http")
    result["http"] = http_probe
    if not http_probe.get("ok"):
        result["error_code"] = http_code
        result["stage"] = "proxy_check_http"
        result["error"] = {"code": http_code, "stage": "proxy_check_http", "message": http_msg or http_probe.get("error")}
        logger.warning(
            "PROXY_CHECK_HTTP_FAIL proxy_id=%s latency_ms=%s code=%s err=%s",
            proxy.id,
            http_probe.get("latency_ms"),
            http_code,
            http_msg,
        )
        return _persist(result)

    logger.info(
        "PROXY_CHECK_HTTP_OK proxy_id=%s latency_ms=%s status=%s exit_ip=%s",
        proxy.id,
        http_probe.get("latency_ms"),
        http_probe.get("status_code"),
        http_probe.get("exit_ip"),
    )

    # Stage 2: HTTPS to confirm CONNECT + TLS handshake
    https_probe, https_code, https_msg = _probe_proxy_stage(proxy_url, IPIFY_HTTPS, "proxy_check_https")
    result["https"] = https_probe
    if not https_probe.get("ok"):
        result["error_code"] = https_code
        result["stage"] = "proxy_check_https"
        result["error"] = {
            "code": https_code,
            "stage": "proxy_check_https",
            "message": https_msg or https_probe.get("error"),
        }
        logger.warning(
            "PROXY_CHECK_HTTPS_FAIL proxy_id=%s latency_ms=%s code=%s err=%s",
            proxy.id,
            https_probe.get("latency_ms"),
            https_code,
            https_msg,
        )
        return _persist(result)

    logger.info(
        "PROXY_CHECK_HTTPS_OK proxy_id=%s latency_ms=%s status=%s exit_ip=%s",
        proxy.id,
        https_probe.get("latency_ms"),
        https_probe.get("status_code"),
        https_probe.get("exit_ip"),
    )

    # Success
    result["ok"] = True
    result["stage"] = "proxy_check_https"
    result["exit_ip"] = https_probe.get("exit_ip") or http_probe.get("exit_ip")
    result["elapsed_ms"] = https_probe.get("latency_ms")
    return _persist(result)


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
        (ProxyEndpoint.unhealthy_until.is_(None) | (ProxyEndpoint.unhealthy_until <= now))
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
    proxy.last_check_at = datetime.utcnow()
    proxy.last_check_status = "failed"
    proxy.last_error = error[:500]
    db.add(proxy)
    db.commit()


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
        "created_at": proxy.created_at,
        "updated_at": proxy.updated_at,
    }
