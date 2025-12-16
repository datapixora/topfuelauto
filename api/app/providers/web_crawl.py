import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, List, Tuple
from urllib.parse import urlencode, urljoin, urlparse

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


def _now_ms() -> float:
    return time.time() * 1000


@dataclass
class _DomainLimit:
    last_reset_ms: float
    count: int


class _AnchorExtractor(HTMLParser):
    """
    Minimal HTML anchor extractor to avoid heavy dependencies.
    """

    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self._current_href = href
                self._current_text = []

    def handle_endtag(self, tag: str):
        if tag.lower() == "a" and self._current_href:
            text = unescape("".join(self._current_text)).strip()
            self.links.append((self._current_href, text))
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str):
        if self._current_href:
            self._current_text.append(data)


class WebCrawlOnDemandProvider:
    """
    Async crawl provider; returns metadata only and defers actual crawl to Celery.
    """

    name = "web_crawl_on_demand"
    supports_free_text = True
    requires_structured = False

    def __init__(self, settings: Settings, config: Dict[str, Any] | None = None):
        self.settings = settings
        self.config = config or {}
        self.enabled = bool(self._allowlist())

    def search_listings(
        self,
        query: str,
        filters: Dict[str, Any],
        page: int,
        page_size: int,
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """
        Synchronous path never crawls; it only returns metadata telling the API
        to rely on the async job. The API decides when to enqueue.
        """
        if not self.enabled:
            return [], 0, {"name": self.name, "enabled": False, "message": "Crawl disabled"}

        return [], 0, {
            "name": self.name,
            "enabled": True,
            "total": 0,
            "message": "async_pending",
        }

    # ---------- Helpers used by the Celery task ----------
    def _rate_limiter(self):
        per_minute = max(1, self._config_value("rate_per_minute", self.settings.crawl_search_rate_per_minute))
        window_ms = 60_000
        state: dict[str, _DomainLimit] = {}

        def allow(domain: str) -> bool:
            now_ms = _now_ms()
            entry = state.get(domain) or _DomainLimit(last_reset_ms=now_ms, count=0)
            if now_ms - entry.last_reset_ms > window_ms:
                entry = _DomainLimit(last_reset_ms=now_ms, count=0)
            if entry.count >= per_minute:
                state[domain] = entry
                return False
            entry.count += 1
            state[domain] = entry
            return True

        return allow

    def crawl_sources(self, query: str) -> list[dict[str, Any]]:
        """
        Lightweight crawl across allowlisted URL templates.
        """
        if not self.enabled:
            return []

        allow = self._rate_limiter()
        results: list[dict[str, Any]] = []
        templates = self._allowlist()
        max_sources = max(1, self._config_value("max_sources", self.settings.crawl_search_max_sources))

        for template in templates[:max_sources]:
            template = template.strip()
            if not template:
                continue
            filled = template.format(query=urlencode({"q": query}).split("=", 1)[1])
            domain = urlparse(filled).netloc
            if not domain:
                continue

            if not allow(domain):
                logger.info("Crawl rate-limited for domain=%s", domain)
                continue

            try:
                resp = httpx.get(
                    filled,
                    headers={"User-Agent": "TopFuelAuto/1.0 (+https://topfuelauto.com)"},
                    timeout=10.0,
                    follow_redirects=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Crawl fetch failed: domain=%s error=%s", domain, exc)
                continue

            if resp.status_code in (403, 429):
                logger.warning("Crawl blocked: domain=%s status=%s", domain, resp.status_code)
                continue

            content_type = resp.headers.get("content-type", "")
            body = resp.text or ""
            if "text/html" not in content_type.lower() and "<html" not in body.lower():
                logger.info("Crawl skipped non-HTML response domain=%s", domain)
                continue

            links = self._extract_links(body, base_url=resp.url.host if resp.url else None)
            for link, text in links:
                parsed = urlparse(link)
                link_domain = parsed.netloc or domain
                normalized_url = link if parsed.scheme else urljoin(f"https://{domain}", link)
                item = self._to_result(link_domain, normalized_url, text)
                results.append(item)

        return results

    @staticmethod
    def _extract_links(html: str, base_url: str | None = None) -> list[tuple[str, str]]:
        parser = _AnchorExtractor()
        parser.feed(html)
        links = []
        for href, text in parser.links:
            if not href:
                continue
            links.append((href, text or "Listing"))
        return links

    @staticmethod
    def _to_result(domain: str, url: str, title: str) -> dict[str, Any]:
        title = title.strip() or "Listing"
        year = None
        make = None
        model = None
        year_match = re.search(r"\b(19|20)\d{2}\b", title)
        if year_match:
            try:
                year = int(year_match.group(0))
            except Exception:
                year = None
        return {
            "title": title[:255],
            "year": year,
            "make": make,
            "model": model,
            "price": None,
            "location": None,
            "source_domain": domain,
            "url": url,
            "fetched_at": datetime.utcnow(),
        }

    def _config_value(self, key: str, default: Any):
        return self.config.get(key, default)

    def _allowlist(self) -> list[str]:
        # Prefer DB config; fallback to env allowlist
        allow = self.config.get("allowlist")
        if allow is not None:
            return allow
        return self.settings.crawl_search_allowlist or []

