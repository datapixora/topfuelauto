from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Tuple
from urllib.parse import urlparse
import logging

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.admin_source import AdminSource
from app.services import data_engine_service, proxy_service

logger = logging.getLogger(__name__)


HTML_TOO_SMALL_THRESHOLD = 1000


@dataclass(frozen=True)
class FetchAttempt:
    method: str
    status_code: Optional[int]
    final_url: Optional[str]
    html_len: int
    blocked: bool
    block_reason: Optional[str]
    error: Optional[str]


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _detect_block(status_code: Optional[int], final_url: str, html: str) -> Tuple[bool, Optional[str]]:
    if not status_code:
        return False, None

    lower = (html or "").lower()
    final_url_lower = (final_url or "").lower()

    block_keywords = {
        "_incapsula_resource": "incapsula",
        "imperva": "imperva",
        "cloudflare challenge": "cloudflare",
        "captcha": "captcha",
        "access denied": "access_denied",
        "blocked by": "blocked_by",
        "rate limit": "rate_limit",
    }

    for keyword, reason_suffix in block_keywords.items():
        if keyword in lower:
            return True, f"keyword_match:{reason_suffix}"

    if "/cdn-cgi/challenge-platform" in final_url_lower:
        return True, "keyword_match:cloudflare_redirect"

    if status_code in (401, 403, 429, 503):
        return True, f"http_status:{status_code}"

    return False, None


def _compute_fingerprints(html: str) -> dict:
    lower = (html or "").lower()
    jsonld = False
    try:
        soup = BeautifulSoup(html or "", "lxml")
        jsonld = any((tag.get("type") or "").lower() == "application/ld+json" for tag in soup.find_all("script"))
    except Exception:
        # Fallback to substring check if parser errors for any reason.
        jsonld = "application/ld+json" in lower
    return {
        "next_data": "__next_data__" in lower,
        "jsonld": jsonld,
        "wp": "wp-content" in lower,
        "woocommerce": "woocommerce" in lower,
        "shopify": ("cdn.shopify.com" in lower) or ("Shopify" in (html or "")),
    }


def _build_candidates(fingerprints: dict) -> list[dict]:
    candidates: list[dict] = []

    if fingerprints.get("next_data"):
        candidates.append({
            "strategy_key": "nextjs_json",
            "confidence": 0.92,
            "reason": "Found __NEXT_DATA__ script marker (Next.js).",
        })

    if fingerprints.get("woocommerce"):
        conf = 0.9 if fingerprints.get("wp") else 0.85
        candidates.append({
            "strategy_key": "woocommerce",
            "confidence": conf,
            "reason": "Found WooCommerce markers in HTML."
            + (" Also found wp-content (WordPress)." if fingerprints.get("wp") else ""),
        })

    if fingerprints.get("shopify"):
        candidates.append({
            "strategy_key": "shopify",
            "confidence": 0.9,
            "reason": "Found Shopify markers (cdn.shopify.com or Shopify).",
        })

    if fingerprints.get("jsonld"):
        candidates.append({
            "strategy_key": "jsonld_product_list",
            "confidence": 0.6,
            "reason": "Found application/ld+json scripts (JSON-LD).",
        })

    # Always include a fallback candidate so the UI has a safe default.
    candidates.append({
        "strategy_key": "generic_html_list",
        "confidence": 0.2,
        "reason": "Fallback: generic HTML list parsing.",
    })

    return candidates


def _pick_best_candidate(candidates: list[dict]) -> Optional[dict]:
    if not candidates:
        return None

    priority = {
        "nextjs_json": 5,
        "shopify": 4,
        "woocommerce": 3,
        "jsonld_product_list": 2,
        "generic_html_list": 1,
    }

    return sorted(
        candidates,
        key=lambda c: (float(c.get("confidence") or 0), priority.get(c.get("strategy_key", ""), 0)),
        reverse=True,
    )[0]


def _choose_better_attempt(a: Tuple[FetchAttempt, str], b: Tuple[FetchAttempt, str]) -> Tuple[FetchAttempt, str]:
    attempt_a, html_a = a
    attempt_b, html_b = b

    # Prefer attempts without errors.
    if attempt_a.error and not attempt_b.error:
        return b
    if attempt_b.error and not attempt_a.error:
        return a

    # Prefer non-blocked attempts.
    if attempt_a.blocked and not attempt_b.blocked:
        return b
    if attempt_b.blocked and not attempt_a.blocked:
        return a

    # Prefer larger HTML bodies.
    if attempt_b.html_len > attempt_a.html_len:
        return b
    return a


def _httpx_fetch(
    url: str,
    proxy_url: Optional[str] = None,
    *,
    timeout_seconds: float = 15.0,
    headers: Optional[dict] = None,
) -> Tuple[FetchAttempt, str]:
    request_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache",
    }
    if isinstance(headers, dict):
        request_headers.update({k: str(v) for k, v in headers.items() if v is not None})

    client_kwargs: dict[str, Any] = {
        "follow_redirects": True,
        "timeout": httpx.Timeout(float(timeout_seconds)),
    }
    if proxy_url:
        client_kwargs["proxy"] = proxy_url

    html = ""
    status_code: Optional[int] = None
    final_url: Optional[str] = None

    try:
        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url, headers=request_headers)
            status_code = resp.status_code
            final_url = str(resp.url)
            html = resp.text or ""
    except Exception as e:
        logger.info("detect: httpx fetch failed url=%s proxy=%s err=%s", url, bool(proxy_url), str(e))
        attempt = FetchAttempt(
            method="httpx_proxy" if proxy_url else "httpx",
            status_code=status_code,
            final_url=final_url,
            html_len=0,
            blocked=False,
            block_reason=None,
            error=f"{type(e).__name__}: {str(e)}",
        )
        return attempt, ""

    blocked, block_reason = _detect_block(status_code, final_url or "", html)
    attempt = FetchAttempt(
        method="httpx_proxy" if proxy_url else "httpx",
        status_code=status_code,
        final_url=final_url,
        html_len=len(html),
        blocked=blocked,
        block_reason=block_reason,
        error=None,
    )
    return attempt, html


def _parse_playwright_proxy(proxy_url: str) -> Optional[dict]:
    try:
        parsed = urlparse(proxy_url)
    except Exception:
        return None

    if parsed.scheme not in ("http", "https", "socks5", "socks5h"):
        return None

    server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}" if parsed.hostname and parsed.port else None
    if not server:
        return None

    proxy: dict[str, Any] = {"server": server}
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    return proxy


def _playwright_fetch(
    url: str,
    proxy_url: Optional[str] = None,
    *,
    timeout_ms: int = 15000,
    headers: Optional[dict] = None,
) -> Tuple[FetchAttempt, str]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:
        return (
            FetchAttempt(
                method="playwright",
                status_code=None,
                final_url=None,
                html_len=0,
                blocked=False,
                block_reason=None,
                error=f"playwright_unavailable:{type(e).__name__}",
            ),
            "",
        )

    html = ""
    status_code: Optional[int] = None
    final_url: Optional[str] = None

    proxy_cfg = _parse_playwright_proxy(proxy_url) if proxy_url else None
    user_agent: Optional[str] = None
    extra_headers: dict[str, str] = {}
    if isinstance(headers, dict):
        for k, v in headers.items():
            if v is None:
                continue
            if str(k).lower() == "user-agent":
                user_agent = str(v)
            else:
                extra_headers[str(k)] = str(v)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy=proxy_cfg)
            context_kwargs: dict[str, Any] = {"ignore_https_errors": True}
            if user_agent:
                context_kwargs["user_agent"] = user_agent
            if extra_headers:
                context_kwargs["extra_http_headers"] = extra_headers
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            status_code = response.status if response else None
            final_url = page.url
            html = page.content() or ""
            context.close()
            browser.close()
    except Exception as e:
        logger.info("detect: playwright fetch failed url=%s err=%s", url, str(e))
        attempt = FetchAttempt(
            method="playwright",
            status_code=status_code,
            final_url=final_url,
            html_len=0,
            blocked=False,
            block_reason=None,
            error=f"{type(e).__name__}: {str(e)}",
        )
        return attempt, ""

    blocked, block_reason = _detect_block(status_code, final_url or "", html)
    attempt = FetchAttempt(
        method="playwright",
        status_code=status_code,
        final_url=final_url,
        html_len=len(html),
        blocked=blocked,
        block_reason=block_reason,
        error=None,
    )
    return attempt, html


def _resolve_proxy_url(db: Session, source: AdminSource) -> Optional[str]:
    proxy_mode = str(source.proxy_mode).upper() if source.proxy_mode else "NONE"

    if proxy_mode == "POOL":
        if not source.proxy_id:
            return None
        proxy = proxy_service.get_proxy(db, source.proxy_id)
        if not proxy:
            return None
        return proxy_service.build_proxy_url(proxy)

    if proxy_mode == "MANUAL":
        settings_json = source.settings_json or {}
        settings_json = data_engine_service.decrypt_proxy_settings(settings_json)

        proxy_url = settings_json.get("proxy_url")
        if proxy_url:
            if settings_json.get("proxy_username") and settings_json.get("proxy_password"):
                parsed = urlparse(proxy_url)
                netloc = parsed.netloc
                if "@" in netloc:
                    netloc = netloc.split("@", 1)[-1]
                return parsed._replace(
                    netloc=f"{settings_json['proxy_username']}:{settings_json['proxy_password']}@{netloc}"
                ).geturl()
            return proxy_url

        if settings_json.get("proxy_host"):
            scheme = settings_json.get("proxy_type", "http")
            host = settings_json["proxy_host"]
            port = settings_json.get("proxy_port", 80)
            user = settings_json.get("proxy_username") or ""
            pwd = settings_json.get("proxy_password") or ""
            if user and pwd:
                return f"{scheme}://{user}:{pwd}@{host}:{port}"
            return f"{scheme}://{host}:{port}"

    return None


def detect_source(
    db: Session,
    source: AdminSource,
    url_override: Optional[str] = None,
    *,
    use_proxy: bool = False,
    use_playwright: bool = False,
    timeout_s: float = 15.0,
    headers: Optional[dict] = None,
) -> dict:
    target_url = (url_override or source.base_url or "").strip()
    if not target_url:
        raise ValueError("Missing URL (source.base_url empty and no override provided)")
    if not _is_http_url(target_url):
        raise ValueError("Invalid URL (must be http/https)")

    attempts: list[FetchAttempt] = []

    best_attempt, best_html = _httpx_fetch(target_url, timeout_seconds=timeout_s, headers=headers)
    attempts.append(best_attempt)

    def should_fallback(attempt: FetchAttempt) -> bool:
        if attempt.error:
            return True
        if attempt.blocked:
            return True
        if attempt.status_code == 200 and attempt.html_len < HTML_TOO_SMALL_THRESHOLD:
            return True
        return False

    proxy_url: Optional[str] = None
    if use_proxy and should_fallback(best_attempt):
        proxy_url = _resolve_proxy_url(db, source)
        if proxy_url:
            proxy_attempt, proxy_html = _httpx_fetch(
                target_url,
                proxy_url=proxy_url,
                timeout_seconds=timeout_s,
                headers=headers,
            )
            attempts.append(proxy_attempt)
            best_attempt, best_html = _choose_better_attempt((best_attempt, best_html), (proxy_attempt, proxy_html))
        else:
            attempts.append(
                FetchAttempt(
                    method="httpx_proxy",
                    status_code=None,
                    final_url=None,
                    html_len=0,
                    blocked=False,
                    block_reason=None,
                    error="proxy_not_configured",
                )
            )

    if use_playwright and should_fallback(best_attempt):
        pw_attempt, pw_html = _playwright_fetch(
            target_url,
            proxy_url=proxy_url if use_proxy else None,
            timeout_ms=int(float(timeout_s) * 1000),
            headers=headers,
        )
        attempts.append(pw_attempt)
        best_attempt, best_html = _choose_better_attempt((best_attempt, best_html), (pw_attempt, pw_html))

    fingerprints = _compute_fingerprints(best_html)
    candidates = _build_candidates(fingerprints)
    best_candidate = _pick_best_candidate(candidates)
    detected_strategy = best_candidate["strategy_key"] if best_candidate else "generic_html_list"

    final_url = best_attempt.final_url or target_url
    suggested_settings_patch: dict[str, Any] = {
        "targets": {"test_url": final_url},
        "fetch": {
            "use_proxy": bool(use_proxy),
            "use_playwright": bool(use_playwright),
            "timeout_s": float(timeout_s),
        },
        "detected_strategy": detected_strategy,
        "extract": {
            "strategy": detected_strategy,
            "list": {"item_selector": "", "next_page_selector": ""},
            "fields": {
                "title": {"selector": "", "attr": "text"},
                "price": {"selector": "", "attr": "text"},
                "url": {"selector": "", "attr": "href"},
                "image": {"selector": "", "attr": "src"},
            },
            "normalize": {},
        },
    }
    if isinstance(headers, dict) and headers:
        suggested_settings_patch["fetch"]["headers"] = headers

    snippet = (best_html or "")[:200]
    report = {
        "source_id": source.id,
        "source_key": source.key,
        "requested_url": url_override,
        "url": target_url,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "fetch": {
            "method": best_attempt.method,
            "status_code": best_attempt.status_code,
            "final_url": best_attempt.final_url,
            "html_len": best_attempt.html_len,
        },
        "snippet": snippet,
        "fingerprints": fingerprints,
        "candidates": candidates,
        "detected_strategy": detected_strategy,
        "suggested_settings_patch": suggested_settings_patch,
        "attempts": [
            {
                "method": a.method,
                "status_code": a.status_code,
                "final_url": a.final_url,
                "html_len": a.html_len,
                "blocked": a.blocked,
                "block_reason": a.block_reason,
                "error": a.error,
            }
            for a in attempts
        ],
    }
    return report
