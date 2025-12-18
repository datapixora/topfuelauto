"""HTTP-based fetcher using httpx."""

import time
import random
import logging
from typing import Optional
import httpx

from ..fetch_diagnostics import FetchDiagnostics

logger = logging.getLogger(__name__)


class HttpFetcher:
    """
    Fetch HTML using HTTP client (httpx).

    Fast, lightweight fetcher with rate limiting and realistic headers.
    Falls back to this mode when browser is not needed.
    """

    def __init__(self, rate_limit_per_minute: int = 30):
        """
        Initialize HTTP fetcher with rate limiting.

        Args:
            rate_limit_per_minute: Maximum requests per minute (default: 30)
        """
        self.rate_limit = rate_limit_per_minute
        self.last_request_time = 0.0

    def fetch(self, url: str, proxy_url: Optional[str] = None, timeout: float = 10.0) -> FetchDiagnostics:
        """
        Fetch HTML using httpx with rate limiting.

        Args:
            url: Target URL to fetch
            proxy_url: Optional proxy URL
            timeout: Request timeout in seconds

        Returns:
            FetchDiagnostics with HTML and metadata

        Raises:
            httpx.HTTPStatusError: If HTTP request fails
        """
        # Rate limiting with jitter
        min_interval = 60.0 / self.rate_limit
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed + random.uniform(0, 0.5)
            time.sleep(sleep_time)

        start_time = time.time()

        # Realistic browser headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            if proxy_url:
                with httpx.Client(proxy=proxy_url, timeout=timeout, follow_redirects=True) as client:
                    response = client.get(url, headers=headers)
            else:
                response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)

            self.last_request_time = time.time()
            latency_ms = int((time.time() - start_time) * 1000)

            response.raise_for_status()

            # Try to get exit IP if proxy was used
            proxy_exit_ip = None
            if proxy_url:
                proxy_exit_ip = self._get_exit_ip(proxy_url, timeout)

            logger.info(
                f"HTTP fetch completed: {url} -> {response.status_code} "
                f"({latency_ms}ms, proxy={bool(proxy_url)})"
            )

            return FetchDiagnostics(
                html=response.text,
                status_code=response.status_code,
                latency_ms=latency_ms,
                fetch_mode="http",
                final_url=str(response.url),
                error=None,
                proxy_exit_ip=proxy_exit_ip,
                browser_version=None,
            )

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"HTTP {e.response.status_code}: {str(e)}"
            logger.error(f"HTTP fetch failed for {url}: {e}", exc_info=True)

            return FetchDiagnostics(
                html="",
                status_code=e.response.status_code,
                latency_ms=latency_ms,
                fetch_mode="http",
                final_url=url,
                error=error_msg,
                proxy_exit_ip=None,
                browser_version=None,
            )

        except httpx.ProxyError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Proxy error: {str(e)}"
            logger.error(f"HTTP proxy error for {url}: {e}", exc_info=True)

            return FetchDiagnostics(
                html="",
                status_code=0,
                latency_ms=latency_ms,
                fetch_mode="http",
                final_url=url,
                error=error_msg,
                proxy_exit_ip=None,
                browser_version=None,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"HTTP fetch exception for {url}: {e}", exc_info=True)

            return FetchDiagnostics(
                html="",
                status_code=0,
                latency_ms=latency_ms,
                fetch_mode="http",
                final_url=url,
                error=error_msg,
                proxy_exit_ip=None,
                browser_version=None,
            )

    def _get_exit_ip(self, proxy_url: str, timeout: float = 5.0) -> Optional[str]:
        """
        Get exit IP via ipify.org through proxy.

        Args:
            proxy_url: Proxy URL to test
            timeout: Request timeout

        Returns:
            Exit IP address, or None if detection fails
        """
        try:
            with httpx.Client(proxy=proxy_url, timeout=timeout) as client:
                response = client.get("https://api.ipify.org?format=text")
                response.raise_for_status()
                exit_ip = response.text.strip()

                # Validate IP format (simple check)
                if exit_ip and "." in exit_ip and len(exit_ip) < 16:
                    return exit_ip
        except Exception as e:
            logger.warning(f"Failed to get exit IP via HTTP: {e}")

        return None
