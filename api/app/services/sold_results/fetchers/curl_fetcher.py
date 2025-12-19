"""Curl-based fetcher using curl_cffi for better TLS/JA3/impersonation."""

import time
import logging
from typing import Optional

from curl_cffi import requests as curl_requests  # type: ignore

from ..fetch_diagnostics import FetchDiagnostics

logger = logging.getLogger(__name__)


class CurlFetcher:
    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout

    def fetch(self, url: str, proxy_url: Optional[str] = None, impersonate: str = "chrome120") -> FetchDiagnostics:
        start = time.time()
        proxies = None
        if proxy_url:
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
        try:
            resp = curl_requests.get(
                url,
                impersonate=impersonate,
                timeout=self.timeout,
                proxies=proxies,
                allow_redirects=True,
            )
            latency_ms = int((time.time() - start) * 1000)
            status = resp.status_code
            text = resp.text or ""
            error = None
            if status >= 400:
                error = f"HTTP {status}"
            return FetchDiagnostics(
                html=text,
                status_code=status,
                latency_ms=latency_ms,
                fetch_mode="curl",
                final_url=url,
                error=error,
                proxy_exit_ip=None,
                browser_version=None,
                attempts=None,
            )
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error("Curl fetch failed %s err=%s", url, e, exc_info=True)
            return FetchDiagnostics(
                html="",
                status_code=0,
                latency_ms=latency_ms,
                fetch_mode="curl",
                final_url=url,
                error=f"{type(e).__name__}: {e}",
                proxy_exit_ip=None,
                browser_version=None,
                attempts=None,
            )
