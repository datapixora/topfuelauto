from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional, Tuple
from urllib.parse import urljoin
from urllib.parse import urlparse
import logging
import json
import re

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
    use_proxy: bool
    status_code: Optional[int]
    final_url: Optional[str]
    html_len: int
    title: Optional[str]
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
    signals = _compute_signals(html)
    return _fingerprints_from_signals(signals)


def _iter_json_nodes(value: Any):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from _iter_json_nodes(v)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_nodes(item)


def _types_for_jsonld_node(node: dict) -> list[str]:
    raw = node.get("@type") or node.get("type")
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(x) for x in raw if isinstance(x, (str, int, float))]
    return []


def _compute_signals(html: str) -> dict[str, Any]:
    """
    Extract robust detection signals from HTML for Detect v2.
    """
    lower = (html or "").lower()

    try:
        soup = BeautifulSoup(html or "", "lxml")
    except Exception:
        soup = None

    # JSON-LD signals (counts + @type set)
    jsonld_count = 0
    jsonld_types: set[str] = set()
    has_product = False
    has_itemlist = False

    if soup is not None:
        jsonld_scripts = [
            tag
            for tag in soup.find_all("script")
            if (tag.get("type") or "").lower() == "application/ld+json"
        ]
        jsonld_count = len(jsonld_scripts)

        for script in jsonld_scripts[:25]:
            txt = (script.string or script.get_text() or "").strip()
            if not txt:
                continue
            try:
                data = json.loads(txt)
            except Exception:
                continue

            for node in _iter_json_nodes(data):
                if not isinstance(node, dict):
                    continue
                for t in _types_for_jsonld_node(node):
                    t_norm = str(t).strip()
                    if not t_norm:
                        continue
                    jsonld_types.add(t_norm)
                    t_lower = t_norm.lower()
                    if t_lower == "product":
                        has_product = True
                    if t_lower == "itemlist":
                        has_itemlist = True

    # Backstop detection for malformed html: still treat presence of any ld+json marker as jsonld present.
    if jsonld_count == 0 and "application/ld+json" in lower:
        jsonld_count = 1

    # Platform scores
    wp_score = min(
        1.0,
        (0.55 if "wp-content" in lower else 0.0)
        + (0.35 if "wp-json" in lower else 0.0)
        + (0.25 if "/wp-admin" in lower else 0.0)
        + (0.25 if "wordpress" in lower and "generator" in lower else 0.0),
    )

    woocommerce_score = min(
        1.0,
        (0.55 if "woocommerce" in lower else 0.0)
        + (0.35 if "woocommerce-price-amount" in lower else 0.0)
        + (0.20 if "add-to-cart" in lower else 0.0)
        + (0.15 if "wc-" in lower else 0.0),
    )

    shopify_score = min(
        1.0,
        (0.65 if "cdn.shopify.com" in lower else 0.0)
        + (0.45 if "window.shopify" in lower else 0.0)
        + (0.20 if "x-shopify" in lower else 0.0)
        + (0.15 if "shopify.theme" in lower else 0.0),
    )

    nextjs_score = 0.0
    if soup is not None and soup.select_one("script#__NEXT_DATA__") is not None:
        nextjs_score = 1.0
    elif "__next_data__" in lower:
        nextjs_score = 0.6

    # Card score: best repeated "item" selector score
    card_score = 0.0
    card_best_selector: Optional[str] = None
    if soup is not None:
        item_candidates = [
            "article.product",
            "li.product",
            "ul.products li.product",
            ".products .product",
            ".product-item",
            ".product-card",
            ".productgrid--item",
            ".grid-product",
            ".product",
            ".card",
            ".listing-item",
            "[data-product-id]",
            "[data-id]",
        ]
        item_candidates = [*item_candidates, *_candidate_selectors_from_product_links(soup)]
        for sel in item_candidates:
            try:
                nodes = soup.select(sel)
            except Exception:
                continue
            if not nodes:
                continue
            score = _score_item_nodes(nodes)
            if score > card_score:
                card_score = score
                card_best_selector = sel

    # Pagination score: simple signals; 0..1
    pagination_score = 0.0
    if soup is not None:
        if soup.select_one("a[rel='next'], link[rel='next']") is not None:
            pagination_score = 1.0
        else:
            hrefs = []
            try:
                hrefs = [a.get("href") for a in soup.find_all("a", href=True)[:500]]
            except Exception:
                hrefs = []
            page_hints = sum(
                1
                for href in hrefs
                if isinstance(href, str) and ("page=" in href.lower() or "/page/" in href.lower())
            )
            if page_hints >= 5:
                pagination_score = 0.7
            elif page_hints >= 1:
                pagination_score = 0.4

    jsonld_types_list = sorted(jsonld_types)
    return {
        "jsonld_count": int(jsonld_count),
        "jsonld_types": jsonld_types_list,
        "has_Product": bool(has_product),
        "has_ItemList": bool(has_itemlist),
        "wp_score": float(wp_score),
        "woocommerce_score": float(woocommerce_score),
        "shopify_score": float(shopify_score),
        "nextjs_score": float(nextjs_score),
        "card_score": float(card_score),
        "card_best_item_selector": card_best_selector,
        "pagination_score": float(pagination_score),
    }


def _fingerprints_from_signals(signals: dict[str, Any]) -> dict[str, bool]:
    jsonld_count = int(signals.get("jsonld_count") or 0)
    return {
        "nextjs": float(signals.get("nextjs_score") or 0) >= 0.5,
        "jsonld": jsonld_count > 0,
        "jsonld_product": bool(signals.get("has_Product")),
        "jsonld_itemlist": bool(signals.get("has_ItemList")),
        "wp": float(signals.get("wp_score") or 0) >= 0.5,
        "woocommerce": float(signals.get("woocommerce_score") or 0) >= 0.5,
        "shopify": float(signals.get("shopify_score") or 0) >= 0.5,
    }


def _build_candidates(fingerprints: dict, signals: dict[str, Any]) -> list[dict]:
    candidates: list[dict] = []

    jsonld_count = int(signals.get("jsonld_count") or 0)
    if fingerprints.get("jsonld_itemlist"):
        conf = min(0.99, 0.88 + (0.02 * min(jsonld_count, 5)))
        candidates.append({
            "strategy_key": "jsonld_itemlist",
            "confidence": conf,
            "reason": "JSON-LD types include ItemList (application/ld+json).",
        })

    if fingerprints.get("jsonld_product"):
        conf = min(0.97, 0.84 + (0.02 * min(jsonld_count, 5)))
        candidates.append({
            "strategy_key": "jsonld_product",
            "confidence": conf,
            "reason": "JSON-LD types include Product (application/ld+json).",
        })

    if fingerprints.get("nextjs"):
        nextjs_score = float(signals.get("nextjs_score") or 0)
        candidates.append({
            "strategy_key": "nextjs",
            "confidence": min(0.85, 0.55 + 0.30 * nextjs_score),
            "reason": "Found __NEXT_DATA__ marker (Next.js).",
        })

    if fingerprints.get("woocommerce"):
        woo_score = float(signals.get("woocommerce_score") or 0)
        conf = min(0.95, 0.3 + 0.7 * woo_score) + (0.03 if fingerprints.get("wp") else 0.0)
        candidates.append({
            "strategy_key": "woocommerce",
            "confidence": conf,
            "reason": "Found WooCommerce markers in HTML."
            + (" Also found wp-content (WordPress)." if fingerprints.get("wp") else ""),
        })

    if fingerprints.get("shopify"):
        shopify_score = float(signals.get("shopify_score") or 0)
        candidates.append({
            "strategy_key": "shopify",
            "confidence": min(0.95, 0.3 + 0.7 * shopify_score),
            "reason": "Found Shopify markers (window.Shopify/cdn.shopify.com/x-shopify).",
        })

    # Always include a fallback candidate so the UI has a safe default.
    card_score = float(signals.get("card_score") or 0)
    candidates.append({
        "strategy_key": "generic_html_list",
        "confidence": max(0.3, min(0.7, 0.3 + 0.4 * card_score)),
        "reason": f"Fallback: generic HTML list parsing (card_score={card_score:.2f}).",
    })

    return candidates


def _pick_best_candidate(candidates: list[dict]) -> Optional[dict]:
    if not candidates:
        return None

    priority = {
        "jsonld_itemlist": 6,
        "jsonld_product": 5,
        "nextjs": 4,
        "shopify": 3,
        "woocommerce": 2,
        "generic_html_list": 1,
    }

    return sorted(
        candidates,
        key=lambda c: (float(c.get("confidence") or 0), priority.get(c.get("strategy_key", ""), 0)),
        reverse=True,
    )[0]


def fetch_best_html(
    db: Session,
    source: AdminSource,
    url: str,
    *,
    try_proxy: bool,
    try_playwright: bool,
    timeout_s: float,
    headers: Optional[dict] = None,
) -> tuple[int, FetchAttempt, str, list[tuple[FetchAttempt, str]]]:
    """
    Try multiple fetch modes and pick the best resulting HTML.

    Attempts (in order):
      1) httpx no proxy
      2) httpx proxy (if try_proxy=True)
      3) playwright no proxy (if try_playwright=True)
      4) playwright proxy (if try_playwright=True and try_proxy=True)
    """
    attempts: list[tuple[FetchAttempt, str]] = []

    # 1) httpx no proxy
    a1, h1 = _httpx_fetch(url, timeout_seconds=timeout_s, headers=headers)
    attempts.append((a1, h1))

    proxy_url: Optional[str] = _resolve_proxy_url(db, source) if try_proxy else None

    # 2) httpx proxy
    if try_proxy:
        if proxy_url:
            a2, h2 = _httpx_fetch(url, proxy_url=proxy_url, timeout_seconds=timeout_s, headers=headers)
            attempts.append((a2, h2))
        else:
            attempts.append(
                (
                    FetchAttempt(
                        method="httpx",
                        use_proxy=True,
                        status_code=None,
                        final_url=None,
                        html_len=0,
                        title=None,
                        blocked=False,
                        block_reason=None,
                        error="proxy_not_configured",
                    ),
                    "",
                )
            )

    # 3) playwright no proxy
    if try_playwright:
        a3, h3 = _playwright_fetch(url, timeout_ms=int(float(timeout_s) * 1000), headers=headers)
        attempts.append((a3, h3))

    # 4) playwright proxy
    if try_playwright and try_proxy and proxy_url:
        a4, h4 = _playwright_fetch(
            url,
            proxy_url=proxy_url,
            timeout_ms=int(float(timeout_s) * 1000),
            headers=headers,
        )
        attempts.append((a4, h4))

    def attempt_score(attempt: FetchAttempt) -> tuple[int, int, int]:
        """
        Higher is better.
        Primary: prefer 200 + not blocked + no error; then <400 + no error; then any non-error; then errors.
        Secondary: prefer larger html_len.
        """
        if attempt.error:
            return (0, 0, attempt.html_len)
        blocked_penalty = 0 if not attempt.blocked else -1
        if attempt.status_code == 200:
            return (3, blocked_penalty, attempt.html_len)
        if attempt.status_code is not None and attempt.status_code < 400:
            return (2, blocked_penalty, attempt.html_len)
        if not attempt.blocked:
            return (1, 0, attempt.html_len)
        return (1, -1, attempt.html_len)

    best_idx = 0
    best_attempt, best_html = attempts[0]
    best_score = attempt_score(best_attempt)
    for idx, (a, h) in enumerate(attempts[1:], start=1):
        score = attempt_score(a)
        if score > best_score:
            best_idx = idx
            best_attempt, best_html = a, h
            best_score = score

    return best_idx, best_attempt, best_html, attempts


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


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _extract_html_title(html: str) -> Optional[str]:
    if not html:
        return None
    m = _TITLE_RE.search(html)
    if not m:
        return None
    title = re.sub(r"\s+", " ", (m.group(1) or "").strip())
    return title or None


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
    title: Optional[str] = None

    try:
        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url, headers=request_headers)
            status_code = resp.status_code
            final_url = str(resp.url)
            html = resp.text or ""
            title = _extract_html_title(html)
    except Exception as e:
        logger.info("detect: httpx fetch failed url=%s proxy=%s err=%s", url, bool(proxy_url), str(e))
        attempt = FetchAttempt(
            method="httpx",
            use_proxy=bool(proxy_url),
            status_code=status_code,
            final_url=final_url,
            html_len=0,
            title=None,
            blocked=False,
            block_reason=None,
            error=f"{type(e).__name__}: {str(e)}",
        )
        return attempt, ""

    blocked, block_reason = _detect_block(status_code, final_url or "", html)
    attempt = FetchAttempt(
        method="httpx",
        use_proxy=bool(proxy_url),
        status_code=status_code,
        final_url=final_url,
        html_len=len(html),
        title=title,
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
                use_proxy=bool(proxy_url),
                status_code=None,
                final_url=None,
                html_len=0,
                title=None,
                blocked=False,
                block_reason=None,
                error=f"playwright_unavailable:{type(e).__name__}",
            ),
            "",
        )

    html = ""
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    title: Optional[str] = None

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
            title = _extract_html_title(html)
            context.close()
            browser.close()
    except Exception as e:
        logger.info("detect: playwright fetch failed url=%s err=%s", url, str(e))
        attempt = FetchAttempt(
            method="playwright",
            use_proxy=bool(proxy_url),
            status_code=status_code,
            final_url=final_url,
            html_len=0,
            title=None,
            blocked=False,
            block_reason=None,
            error=f"{type(e).__name__}: {str(e)}",
        )
        return attempt, ""

    blocked, block_reason = _detect_block(status_code, final_url or "", html)
    attempt = FetchAttempt(
        method="playwright",
        use_proxy=bool(proxy_url),
        status_code=status_code,
        final_url=final_url,
        html_len=len(html),
        title=title,
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


def _looks_like_product_href(href: str) -> bool:
    h = (href or "").lower()
    if not h:
        return False
    # Common product/detail URL patterns across many ecommerce sites.
    return any(
        needle in h
        for needle in (
            "/product",
            "/products/",
            "product=",
            "/p-",
            "/item",
            "/items/",
            "sku=",
        )
    )


_PRICE_RE = re.compile(r"(?<!\\d)(\\d{1,3}(?:[\\.,]\\d{3})+|\\d+)(?!\\d)")
_CURRENCY_TOKENS = ("$", "€", "£", "usd", "eur", "gbp", "toman", "rial", "تومان", "ریال", "تومن")


def _looks_like_price(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    lower = t.lower()
    m = _PRICE_RE.search(lower)
    if not m:
        return False
    if any(tok in lower for tok in _CURRENCY_TOKENS):
        return True

    digits = re.sub(r"\\D", "", m.group(0))
    if len(digits) >= 4:
        return True
    # If no explicit currency token, still accept if it "looks" like a price (has separators)
    return "," in lower or "٫" in lower or "٬" in lower


def _safe_class_fragment(value: str) -> Optional[str]:
    v = (value or "").strip()
    if not v:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", v):
        return None
    # Avoid extremely generic grid/layout classes that tend to over-match.
    if v.lower() in {"row", "col", "container", "wrapper", "grid", "item"}:
        return None
    return v


def _candidate_selectors_from_product_links(soup: BeautifulSoup) -> list[str]:
    counts: dict[str, int] = {}
    for a in soup.find_all("a", href=True)[:2000]:
        href = a.get("href") or ""
        if not _looks_like_product_href(href):
            continue
        # Walk up a few ancestors to find a reasonable "card" container.
        parent = a
        for _ in range(5):
            parent = parent.parent
            if parent is None or not hasattr(parent, "name"):
                break
            if parent.name not in ("li", "article", "div", "section"):
                continue
            classes = parent.get("class") or []
            if not isinstance(classes, (list, tuple)):
                continue
            cls = next((c for c in classes if _safe_class_fragment(str(c))), None)
            if not cls:
                continue
            sel = f"{parent.name}.{cls}"
            counts[sel] = counts.get(sel, 0) + 1
            break

    # Top repeated selectors first.
    return [k for k, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]]


def _score_item_nodes(nodes: list[Any]) -> float:
    count = len(nodes)
    if count < 2:
        return 0.0

    sample = nodes[: min(count, 25)]
    n = len(sample)
    if n == 0:
        return 0.0

    link_hits = 0
    product_link_hits = 0
    price_hits = 0
    img_hits = 0
    title_hits = 0
    text_lens: list[int] = []

    for node in sample:
        try:
            txt = node.get_text(" ", strip=True) if hasattr(node, "get_text") else ""
        except Exception:
            txt = ""
        text_lens.append(len(txt or ""))

        a = None
        try:
            a = node.find("a", href=True) if hasattr(node, "find") else None
        except Exception:
            a = None

        if a is not None and a.get("href"):
            link_hits += 1
            if _looks_like_product_href(str(a.get("href") or "")):
                product_link_hits += 1

        try:
            if _looks_like_price(txt):
                price_hits += 1
        except Exception:
            pass

        try:
            if node.find("img") is not None:
                img_hits += 1
        except Exception:
            pass

        try:
            if node.find(["h1", "h2", "h3", "h4"]) is not None:
                title_hits += 1
            elif node.select_one(".name, .title, .product-title, .product__title") is not None:
                title_hits += 1
        except Exception:
            pass

    link_ratio = link_hits / n
    product_link_ratio = product_link_hits / n
    price_ratio = price_hits / n
    img_ratio = img_hits / n
    title_ratio = title_hits / n

    # Prefer selectors that return a reasonable count of repeated "cards".
    count_score = min(count, 60) / 60.0

    avg_text_len = (sum(text_lens) / n) if n else 0.0
    # Penalize giant containers; those are usually wrappers, not items.
    big_penalty = 0.25 if avg_text_len > 600 else (0.1 if avg_text_len > 350 else 0.0)

    score = (
        (0.50 * count_score)
        + (0.20 * product_link_ratio)
        + (0.10 * link_ratio)
        + (0.12 * price_ratio)
        + (0.06 * img_ratio)
        + (0.02 * title_ratio)
        - big_penalty
    )
    return max(0.0, min(1.0, score))


def _pick_best_item_selector(soup: BeautifulSoup, candidates: list[str]) -> Optional[str]:
    best_sel: Optional[str] = None
    best_score = 0.0
    for sel in candidates:
        try:
            nodes = soup.select(sel)
        except Exception:
            continue
        if not nodes:
            continue
        score = _score_item_nodes(nodes)
        if score > best_score:
            best_score = score
            best_sel = sel
    if best_sel and best_score >= 0.15:
        return best_sel
    return best_sel


def _pick_best_field_selector(
    item_nodes: list[Any],
    selector_candidates: list[str],
    *,
    attr: str,
    value_filter: Optional[Callable[[str], bool]] = None,
) -> Optional[str]:
    best_sel: Optional[str] = None
    best_hits = 0

    sample = item_nodes[: min(len(item_nodes), 25)]
    if not sample:
        return None

    for sel in selector_candidates:
        hits = 0
        for node in sample:
            try:
                target = node.select_one(sel)
            except Exception:
                target = None
            if target is None:
                continue

            try:
                if attr == "text":
                    value = target.get_text(" ", strip=True)
                else:
                    value = target.get(attr)
                    if isinstance(value, (list, tuple)):
                        value = " ".join([str(x) for x in value if x is not None]).strip()
                    value = str(value).strip() if value is not None else ""
            except Exception:
                value = ""

            if not value:
                continue
            if value_filter and not value_filter(value):
                continue
            hits += 1

        if hits > best_hits:
            best_hits = hits
            best_sel = sel

    return best_sel


def _suggest_generic_html_list_extract(
    soup: BeautifulSoup,
    *,
    used_url: str,
    item_selector_candidates: Optional[list[str]] = None,
    title_selector_candidates: Optional[list[str]] = None,
    price_selector_candidates: Optional[list[str]] = None,
    url_selector_candidates: Optional[list[str]] = None,
    image_selector_candidates: Optional[list[str]] = None,
    next_page_selector_candidates: Optional[list[str]] = None,
) -> dict[str, Any]:
    item_candidates = item_selector_candidates or [
        "article.product",
        "li.product",
        ".products .product",
        ".product-item",
        ".product-card",
        ".product",
        "[data-id][data-price]",
    ]

    # Add derived candidates from repeated product-ish links.
    item_candidates = [*item_candidates, *_candidate_selectors_from_product_links(soup)]

    item_selector = _pick_best_item_selector(soup, item_candidates) or ""
    item_nodes: list[Any] = []
    if item_selector:
        try:
            item_nodes = soup.select(item_selector)
        except Exception:
            item_nodes = []

    title_candidates = title_selector_candidates or [
        ".woocommerce-loop-product__title",
        ".product__title",
        ".product-title",
        ".title",
        ".name",
        "h2",
        "h3",
        "h4",
        "a",
    ]
    price_candidates = price_selector_candidates or [
        ".woocommerce-Price-amount",
        ".price",
        ".amount",
        ".money",
        "[data-price]",
    ]
    url_candidates = url_selector_candidates or [
        "a.woocommerce-LoopProduct-link",
        "a[href*='/products/']",
        "a[href*='product']",
        "a[href]",
    ]
    image_candidates = image_selector_candidates or [
        "img.attachment-woocommerce_thumbnail",
        "img",
    ]
    next_page_candidates = next_page_selector_candidates or [
        "a[rel='next']",
        "a.next",
        ".pagination a.next",
        ".woocommerce-pagination a.next",
        ".next.page-numbers",
    ]

    title_selector = _pick_best_field_selector(item_nodes, title_candidates, attr="text") or ""
    price_selector = _pick_best_field_selector(item_nodes, price_candidates, attr="text", value_filter=_looks_like_price) or ""
    url_selector = _pick_best_field_selector(item_nodes, url_candidates, attr="href", value_filter=_looks_like_product_href) or ""
    if not url_selector:
        # Fall back to any href within the item.
        url_selector = _pick_best_field_selector(item_nodes, ["a[href]"], attr="href") or ""
    image_selector = _pick_best_field_selector(item_nodes, image_candidates, attr="src") or ""

    next_page_selector: Optional[str] = None
    for sel in next_page_candidates:
        try:
            a = soup.select_one(sel)
        except Exception:
            a = None
        if a is not None and a.get("href"):
            next_page_selector = sel
            break

    return {
        "strategy": "generic_html_list",
        "list": {
            "item_selector": item_selector,
            **({"next_page_selector": next_page_selector} if next_page_selector else {}),
        },
        "fields": {
            "title": {"selector": title_selector, "attr": "text"},
            "price": {"selector": price_selector, "attr": "text"},
            "url": {"selector": url_selector, "attr": "href"},
            "image": {"selector": image_selector, "attr": "src"},
        },
        "normalize": {},
    }


def _suggest_jsonld_extract(mode: str) -> dict[str, Any]:
    return {
        "strategy": "jsonld",
        "jsonld": {"mode": mode},
        "fields": {
            "title": {"path": "name"},
            "price": {"path": "offers.price"},
            "url": {"path": "url"},
            "image": {"path": "image"},
        },
        "normalize": {},
    }


def _select_detected_strategy(signals: dict[str, Any]) -> str:
    """
    Detect v2 selection rules.

    JSON-LD wins when present (structured signals); otherwise fallback to platform markers and then generic.
    """
    if signals.get("has_ItemList"):
        return "jsonld_itemlist"
    if signals.get("has_Product"):
        return "jsonld_product"
    if float(signals.get("shopify_score") or 0) >= 0.6:
        return "shopify"
    if float(signals.get("woocommerce_score") or 0) >= 0.6:
        return "woocommerce"
    if float(signals.get("nextjs_score") or 0) >= 0.5:
        return "nextjs"
    return "generic_html_list"


def _suggest_extract_for_strategy(detected_strategy: str, soup: BeautifulSoup, *, used_url: str) -> dict[str, Any]:
    if detected_strategy == "jsonld_itemlist":
        return _suggest_jsonld_extract("ItemList")
    if detected_strategy == "jsonld_product":
        return _suggest_jsonld_extract("Product")
    if detected_strategy == "woocommerce":
        return _suggest_generic_html_list_extract(
            soup,
            used_url=used_url,
            item_selector_candidates=[
                "ul.products li.product",
                "li.product",
                ".products .product",
                ".product",
            ],
            title_selector_candidates=[
                "h2.woocommerce-loop-product__title",
                ".woocommerce-loop-product__title",
                ".product__title",
                ".product-title",
                "h3",
                "h2",
                "a",
            ],
            price_selector_candidates=[
                ".price .woocommerce-Price-amount",
                ".woocommerce-Price-amount",
                ".price",
                ".amount",
            ],
            url_selector_candidates=[
                "a.woocommerce-LoopProduct-link",
                "a.woocommerce-loop-product__link",
                "a[href*='product']",
                "a[href]",
            ],
            image_selector_candidates=[
                "img.attachment-woocommerce_thumbnail",
                "img.wp-post-image",
                "img",
            ],
            next_page_selector_candidates=[
                ".woocommerce-pagination a.next",
                ".next.page-numbers",
                "a[rel='next']",
                "a.next",
            ],
        )
    if detected_strategy == "shopify":
        suggested = _suggest_generic_html_list_extract(
            soup,
            used_url=used_url,
            item_selector_candidates=[
                ".product-card",
                ".grid-product",
                ".productgrid--item",
                ".product-item",
                ".product",
            ],
            title_selector_candidates=[
                ".product-card__title",
                ".grid-product__title",
                ".product-title",
                ".product__title",
                ".title",
                "h3",
                "h2",
                "a",
            ],
            price_selector_candidates=[
                ".price",
                ".price-item",
                ".money",
                ".amount",
            ],
            url_selector_candidates=[
                "a[href*='/products/']",
                "a[href*='product']",
                "a[href]",
            ],
            image_selector_candidates=["img", "img[src]"],
            next_page_selector_candidates=[
                "a[rel='next']",
                ".pagination a.next",
                "a.next",
            ],
        )

        # If this looks like a Shopify collection URL, suggest the products.json endpoint.
        try:
            parsed = urlparse(used_url)
            if "/collections/" in (parsed.path or ""):
                suggested["shopify"] = {
                    "products_json_url": urljoin(f"{parsed.scheme}://{parsed.netloc}", f"{parsed.path.rstrip('/')}/products.json")
                }
        except Exception:
            pass
        return suggested

    # nextjs and generic fallback both use DOM card heuristics for now.
    return _suggest_generic_html_list_extract(soup, used_url=used_url)


def detect_from_html(html: str, *, used_url: str) -> dict[str, Any]:
    """
    Pure detection logic for unit tests (no network, no DB).
    """
    signals = _compute_signals(html)
    fingerprints = _fingerprints_from_signals(signals)
    candidates = _build_candidates(fingerprints, signals)
    detected_strategy = _select_detected_strategy(signals)

    soup = BeautifulSoup(html or "", "lxml")
    suggested_extract = _suggest_extract_for_strategy(detected_strategy, soup, used_url=used_url)
    return {
        "signals": signals,
        "fingerprints": fingerprints,
        "candidates": candidates,
        "detected_strategy": detected_strategy,
        "suggested_extract": suggested_extract,
    }


def detect_source(
    db: Session,
    source: AdminSource,
    url_override: Optional[str] = None,
    requested_url: Optional[str] = None,
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

    best_idx, best_attempt, best_html, attempts_with_html = fetch_best_html(
        db,
        source,
        target_url,
        try_proxy=bool(use_proxy),
        try_playwright=bool(use_playwright),
        timeout_s=float(timeout_s),
        headers=headers,
    )
    used_url = best_attempt.final_url or target_url

    analysis = detect_from_html(best_html or "", used_url=used_url)
    signals = analysis["signals"]
    fingerprints = analysis["fingerprints"]
    candidates = analysis["candidates"]
    detected_strategy = analysis["detected_strategy"]
    suggested_extract = analysis["suggested_extract"]

    suggested_settings_patch: dict[str, Any] = {
        "targets": {"test_url": used_url},
        "fetch": {
            "use_proxy": bool(use_proxy),
            "use_playwright": bool(use_playwright),
            "timeout_s": float(timeout_s),
        },
        "detected_strategy": detected_strategy,
        "extract": suggested_extract,
    }
    if isinstance(headers, dict) and headers:
        suggested_settings_patch["fetch"]["headers"] = headers

    snippet = (best_html or "")[:200]
    report = {
        "source_id": source.id,
        "source_key": source.key,
        "requested_url": requested_url,
        "url": target_url,
        "used_url": used_url,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "fetch": {
            "method": best_attempt.method,
            "status_code": best_attempt.status_code,
            "final_url": best_attempt.final_url,
            "html_len": best_attempt.html_len,
            "title": best_attempt.title,
        },
        "snippet": snippet,
        "fingerprints": fingerprints,
        "signals": signals,
        "candidates": candidates,
        "detected_strategy": detected_strategy,
        "suggested_settings_patch": suggested_settings_patch,
        "attempts": [
            {
                "method": a.method,
                "use_proxy": a.use_proxy,
                "status_code": a.status_code,
                "final_url": a.final_url,
                "html_len": a.html_len,
                "title": a.title,
                "blocked": a.blocked,
                "block_reason": a.block_reason,
                "error": a.error,
                "chosen_best": idx == best_idx,
            }
            for idx, (a, _h) in enumerate(attempts_with_html)
        ],
    }
    return report
