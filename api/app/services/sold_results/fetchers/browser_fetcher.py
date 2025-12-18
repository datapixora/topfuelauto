"""Browser-based fetcher using Playwright Chromium."""

import time
import logging
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Error as PlaywrightError

from ..fetch_diagnostics import FetchDiagnostics

logger = logging.getLogger(__name__)


class BrowserFetcher:
    """
    Fetch HTML using headless Chromium via Playwright.

    Provides browser-like fetching to bypass bot detection and Cloudflare blocks.
    Supports proxy and captures detailed diagnostics.
    """

    def __init__(self, headless: bool = True, timeout_ms: int = 30000):
        """
        Initialize browser fetcher.

        Args:
            headless: Run browser in headless mode (default: True)
            timeout_ms: Page load timeout in milliseconds (default: 30000)
        """
        self.headless = headless
        self.timeout_ms = timeout_ms

    def fetch(self, url: str, proxy_url: Optional[str] = None) -> FetchDiagnostics:
        """
        Fetch HTML using Playwright Chromium.

        Args:
            url: Target URL to fetch
            proxy_url: Optional proxy URL (e.g., http://user:pass@host:port)

        Returns:
            FetchDiagnostics with HTML and metadata

        Raises:
            PlaywrightError: If browser operation fails
            TimeoutError: If page load exceeds timeout
        """
        start_time = time.time()
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            with sync_playwright() as p:
                logger.warning("PLAYWRIGHT BROWSER FETCH EXECUTED")
                # Parse proxy if provided
                proxy_config = None
                if proxy_url:
                    proxy_config = self._parse_proxy_url(proxy_url)

                # Launch browser
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )

                # Create context with proxy
                context = browser.new_context(
                    proxy=proxy_config,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                )

                # Create page and navigate
                page = context.new_page()
                page.set_default_timeout(self.timeout_ms)

                response = page.goto(url, wait_until='domcontentloaded')

                if not response:
                    raise PlaywrightError("Navigation failed: no response")

                # Capture diagnostics
                status_code = response.status
                final_url = page.url
                html = page.content()
                latency_ms = int((time.time() - start_time) * 1000)
                browser_version = browser.version

                # Try to get exit IP if proxy was used
                proxy_exit_ip = None
                if proxy_url:
                    proxy_exit_ip = self._get_exit_ip(page)

                logger.info(
                    f"Browser fetch completed: {url} -> {status_code} "
                    f"({latency_ms}ms, proxy={bool(proxy_url)})"
                )

                return FetchDiagnostics(
                    html=html,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    fetch_mode="browser",
                    final_url=final_url,
                    error=None,
                    proxy_exit_ip=proxy_exit_ip,
                    browser_version=browser_version,
                )

        except PlaywrightError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            msg = str(e)
            if "executable doesn't exist" in msg or "chromium" in msg.lower():
                error_msg = "Browser fetch unavailable (Chromium not installed)"
            else:
                error_msg = f"Playwright error: {msg}"
            logger.error(f"Browser fetch failed for {url}: {e}", exc_info=True)

            return FetchDiagnostics(
                html="",
                status_code=0,
                latency_ms=latency_ms,
                fetch_mode="browser",
                final_url=url,
                error=error_msg,
                proxy_exit_ip=None,
                browser_version=None,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Browser fetch exception for {url}: {e}", exc_info=True)

            return FetchDiagnostics(
                html="",
                status_code=0,
                latency_ms=latency_ms,
                fetch_mode="browser",
                final_url=url,
                error=error_msg,
                proxy_exit_ip=None,
                browser_version=None,
            )

        finally:
            # Cleanup resources
            if page:
                page.close()
            if context:
                context.close()
            if browser:
                browser.close()

    def _parse_proxy_url(self, proxy_url: str) -> dict:
        """
        Parse proxy URL into Playwright proxy config.

        Args:
            proxy_url: Proxy URL (e.g., http://user:pass@host:port)

        Returns:
            Playwright proxy configuration dict
        """
        # Example: http://user:pass@proxy.example.com:8080
        # Playwright expects: {"server": "http://proxy.example.com:8080", "username": "user", "password": "pass"}

        from urllib.parse import urlparse

        parsed = urlparse(proxy_url)

        config = {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        }

        if parsed.username:
            config["username"] = parsed.username
        if parsed.password:
            config["password"] = parsed.password

        return config

    def _get_exit_ip(self, page: Page) -> Optional[str]:
        """
        Get exit IP by navigating to ipify.org.

        Args:
            page: Playwright page instance

        Returns:
            Exit IP address, or None if detection fails
        """
        try:
            # Navigate to ipify in same page (reuses proxy)
            page.goto("https://api.ipify.org?format=text", wait_until="domcontentloaded", timeout=5000)
            exit_ip = page.content().strip()

            # Validate IP format (simple check)
            if exit_ip and "." in exit_ip and len(exit_ip) < 16:
                return exit_ip
        except Exception as e:
            logger.warning(f"Failed to get exit IP: {e}")

        return None
