from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin
import logging

from bs4 import BeautifulSoup

from sqlalchemy.orm import Session

from app.models.admin_source import AdminSource
from app.services import source_detect_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    fetch: dict
    html: str
    errors: list[str]


def _normalize_extract_config(extract: dict) -> dict:
    """
    Normalize extract config to the shape:
    {
      "list": {"item_selector": str, "next_page_selector": str?},
      "fields": { "<name>": {"selector": str, "attr": str?}, ... }
    }
    """
    if not isinstance(extract, dict):
        return {"strategy": None, "list": {}, "fields": {}, "normalize": {}}

    strategy = extract.get("strategy") if isinstance(extract.get("strategy"), str) else None
    list_cfg = extract.get("list") if isinstance(extract.get("list"), dict) else {}
    fields_cfg = extract.get("fields") if isinstance(extract.get("fields"), dict) else {}
    normalize_cfg = extract.get("normalize") if isinstance(extract.get("normalize"), dict) else {}

    # Back-compat: allow top-level item_selector/next_page_selector
    if "item_selector" in extract and "item_selector" not in list_cfg:
        list_cfg = {**list_cfg, "item_selector": extract.get("item_selector")}
    if "next_page_selector" in extract and "next_page_selector" not in list_cfg:
        list_cfg = {**list_cfg, "next_page_selector": extract.get("next_page_selector")}

    return {"strategy": strategy, "list": list_cfg, "fields": fields_cfg, "normalize": normalize_cfg}


def _should_fallback(attempt: source_detect_service.FetchAttempt) -> bool:
    if attempt.error:
        return True
    if attempt.blocked:
        return True
    if attempt.status_code == 200 and attempt.html_len < source_detect_service.HTML_TOO_SMALL_THRESHOLD:
        return True
    return False


def fetch_html_for_source(
    db: Session,
    source: AdminSource,
    url: str,
    *,
    use_proxy: bool = False,
    use_playwright: bool = False,
    timeout_s: float = 15.0,
    headers: Optional[dict] = None,
) -> FetchResult:
    """
    Fetch HTML for a source using the same robust approach as detect:
    - httpx direct first
    - if blocked/error/too-small, retry with configured proxy (if any)
    - if still blocked/error/too-small and try_playwright=True, try Playwright once
    """
    errors: list[str] = []

    best_attempt, best_html = source_detect_service._httpx_fetch(  # noqa: SLF001
        url,
        timeout_seconds=timeout_s,
        headers=headers,
    )
    attempts: list[source_detect_service.FetchAttempt] = [best_attempt]

    proxy_url: Optional[str] = None
    if use_proxy and _should_fallback(best_attempt):
        proxy_url = source_detect_service._resolve_proxy_url(db, source)  # noqa: SLF001
        if proxy_url:
            proxy_attempt, proxy_html = source_detect_service._httpx_fetch(  # noqa: SLF001
                url,
                proxy_url=proxy_url,
                timeout_seconds=timeout_s,
                headers=headers,
            )
            attempts.append(proxy_attempt)
            best_attempt, best_html = source_detect_service._choose_better_attempt(  # noqa: SLF001
                (best_attempt, best_html),
                (proxy_attempt, proxy_html),
            )
        else:
            errors.append("proxy_not_configured")

    if use_playwright and _should_fallback(best_attempt):
        pw_attempt, pw_html = source_detect_service._playwright_fetch(  # noqa: SLF001
            url,
            proxy_url=proxy_url if use_proxy else None,
            timeout_ms=int(float(timeout_s) * 1000),
            headers=headers,
        )
        attempts.append(pw_attempt)
        best_attempt, best_html = source_detect_service._choose_better_attempt(  # noqa: SLF001
            (best_attempt, best_html),
            (pw_attempt, pw_html),
        )

    for a in attempts:
        if a.error:
            errors.append(f"{a.method}: {a.error}")
        elif a.blocked:
            errors.append(f"{a.method}: blocked ({a.block_reason})")

    return FetchResult(
        fetch={
            "method": best_attempt.method,
            "status_code": best_attempt.status_code,
            "final_url": best_attempt.final_url,
            "html_len": best_attempt.html_len,
        },
        html=best_html or "",
        errors=errors,
    )


def _extract_value(node: Any, attr: Optional[str], base_url: Optional[str]) -> Optional[str]:
    if node is None:
        return None

    attr_norm = (attr or "text").strip()
    if not attr_norm or attr_norm == "text":
        txt = node.get_text(" ", strip=True)
        return txt or None

    raw = node.get(attr_norm)
    if raw is None:
        return None

    if isinstance(raw, (list, tuple)):
        raw = " ".join([str(x) for x in raw if x is not None]).strip()

    val = str(raw).strip()
    if not val:
        return None

    if base_url and attr_norm in ("href", "src"):
        try:
            return urljoin(base_url, val)
        except Exception:
            return val

    return val


def extract_generic_html_list(html: str, extract: dict, *, base_url: Optional[str] = None) -> tuple[int, list[dict], list[str]]:
    errors: list[str] = []
    cfg = _normalize_extract_config(extract or {})

    if cfg.get("strategy") and cfg.get("strategy") != "generic_html_list":
        errors.append(f"extract.strategy is '{cfg.get('strategy')}', expected 'generic_html_list'")

    item_selector = (cfg.get("list") or {}).get("item_selector")
    if not isinstance(item_selector, str) or not item_selector.strip():
        return 0, [], [*errors, "Missing extract.list.item_selector"]

    soup = BeautifulSoup(html or "", "lxml")

    try:
        item_nodes = soup.select(item_selector)
    except Exception as e:
        return 0, [], [*errors, f"Invalid item_selector: {type(e).__name__}: {str(e)}"]

    fields: dict = cfg.get("fields") or {}
    items_preview: list[dict] = []

    for node in item_nodes[:5]:
        out: dict[str, Any] = {}
        for field_name, spec in fields.items():
            if not isinstance(spec, dict):
                continue
            selector = spec.get("selector")
            if not isinstance(selector, str) or not selector.strip():
                continue
            attr = spec.get("attr")
            try:
                target = node.select_one(selector)
            except Exception as e:
                errors.append(f"Invalid selector for '{field_name}': {type(e).__name__}: {str(e)}")
                target = None
            out[field_name] = _extract_value(target, attr, base_url)
        items_preview.append(out)

    return len(item_nodes), items_preview, errors


def test_extract(
    db: Session,
    source: AdminSource,
    *,
    url_override: Optional[str] = None,
    extract_override: Optional[dict] = None,
) -> dict:
    settings = source.settings_json or {}
    extract_cfg = extract_override if extract_override is not None else settings.get("extract")
    if not extract_cfg:
        raise ValueError("Missing extract config (provide body.extract or set source.settings_json.extract)")

    targets = settings.get("targets") if isinstance(settings.get("targets"), dict) else {}
    settings_test_url = targets.get("test_url") if isinstance(targets.get("test_url"), str) else None
    target_url = (url_override or settings_test_url or source.base_url or "").strip()
    if not target_url:
        raise ValueError("Missing URL (source.base_url empty and no override provided)")

    fetch_cfg = settings.get("fetch") if isinstance(settings.get("fetch"), dict) else {}
    use_proxy = bool(fetch_cfg.get("use_proxy"))
    use_playwright = bool(fetch_cfg.get("use_playwright"))
    timeout_s_raw = fetch_cfg.get("timeout_s")
    timeout_s = float(timeout_s_raw) if isinstance(timeout_s_raw, (int, float)) else float(getattr(source, "timeout_seconds", 15) or 15)
    headers = fetch_cfg.get("headers") if isinstance(fetch_cfg.get("headers"), dict) else None

    fetch_res = fetch_html_for_source(
        db,
        source,
        target_url,
        use_proxy=use_proxy,
        use_playwright=use_playwright,
        timeout_s=timeout_s,
        headers=headers,
    )

    items_found, items_preview, extract_errors = extract_generic_html_list(
        fetch_res.html,
        extract_cfg,
        base_url=fetch_res.fetch.get("final_url") or target_url,
    )

    errors = [*fetch_res.errors, *extract_errors]
    return {
        "fetch": fetch_res.fetch,
        "items_found": items_found,
        "items_preview": items_preview,
        "errors": errors,
    }
