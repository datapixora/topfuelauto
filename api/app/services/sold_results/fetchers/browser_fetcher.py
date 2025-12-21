"""Browser-based fetcher using Playwright Chromium."""

import os
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

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30000,
        solve_captcha: bool = True,
        slow_mo: int = 0,
        record_trace: bool = False,
    ):
        """
        Initialize browser fetcher.

        Args:
            headless: Run browser in headless mode (default: True)
            timeout_ms: Page load timeout in milliseconds (default: 30000)
            solve_captcha: Attempt to solve CAPTCHA challenges (default: True)
            slow_mo: Slow down operations by specified ms (default: 0, watch mode uses 150)
            record_trace: Enable trace recording for production debugging (default: False)
        """
        # Environment detection
        app_env = os.getenv('APP_ENV', 'development').lower()
        is_production = app_env == 'production'

        # Watch mode safety: force headless in production
        if not headless and is_production:
            logger.warning(
                "Watch mode (headless=False) requested in production environment. "
                "Forcing headless=True for security."
            )
            headless = True
            slow_mo = 0  # Disable slowMo in production

        self.headless = headless
        self.timeout_ms = timeout_ms
        self.slow_mo = slow_mo
        self.record_trace = record_trace or (is_production and not headless)  # Auto-enable trace in prod
        self.is_production = is_production
        self.solve_captcha = solve_captcha and os.getenv('CAPTCHA_SOLVER_ENABLED', 'false').lower() == 'true'
        self.twocaptcha_api_key = os.getenv('TWOCAPTCHA_API_KEY')
        self.cloudflare_timeout = int(os.getenv('CLOUDFLARE_WAIT_TIMEOUT', '60'))
        self.cloudflare_max_retries = int(os.getenv('CLOUDFLARE_MAX_RETRIES', '2'))

    def fetch(
        self,
        url: str,
        proxy_url: Optional[str] = None,
        proxy_id: Optional[int] = None,
        cookies: Optional[str] = None,
        tracking_id: Optional[int] = None,
    ) -> FetchDiagnostics:
        """
        Fetch HTML using Playwright Chromium.

        Args:
            url: Target URL to fetch
            proxy_url: Optional proxy URL (e.g., http://user:pass@host:port)
            proxy_id: Optional proxy identifier for logging/diagnostics
            cookies: Optional cookie string (e.g., "name1=value1; name2=value2")
            tracking_id: Optional tracking ID for artifact naming

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
        artifact_path: Optional[str] = None

        try:
            with sync_playwright() as p:
                logger.info(
                    "BROWSER_FETCH_START url=%s proxy_id=%s fetch_mode=browser",
                    url,
                    proxy_id,
                )
                # Parse proxy if provided
                proxy_config = None
                if proxy_url:
                    proxy_config = self._parse_proxy_url(proxy_url)

                # Launch browser with slow_mo if enabled
                launch_options = {
                    'headless': self.headless,
                    'proxy': proxy_config,
                    'args': [
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                }

                # Add slow_mo for watch mode
                if self.slow_mo > 0:
                    launch_options['slow_mo'] = self.slow_mo
                    logger.info(f"Browser slow_mo enabled: {self.slow_mo}ms")

                browser = p.chromium.launch(**launch_options)

                # Create context
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York',
                )

                # Start tracing if enabled (production debugging)
                if self.record_trace and tracking_id:
                    trace_dir = os.path.join('api', 'artifacts', 'traces', str(tracking_id))
                    os.makedirs(trace_dir, exist_ok=True)
                    artifact_path = os.path.join(trace_dir, 'trace.zip')

                    context.tracing.start(screenshots=True, snapshots=True, sources=True)
                    logger.info(f"Trace recording started, will save to: {artifact_path}")

                # Block heavy resources
                def _block_route(route):
                    if route.request.resource_type in ("image", "font", "media", "stylesheet"):
                        return route.abort()
                    return route.continue_()

                # Create page and navigate
                page = context.new_page()
                page.set_default_timeout(self.timeout_ms)
                page.route("**/*", _block_route)

                # Inject cookies if provided, or load from environment
                cookies_to_use = cookies or os.getenv('BIDFAX_COOKIES')
                if cookies_to_use:
                    cookie_list = self._parse_cookies(url, cookies_to_use)
                    context.add_cookies(cookie_list)
                    source = "parameter" if cookies else "environment"
                    logger.info(f"Injected {len(cookie_list)} cookies from {source}")

                response = page.goto(
                    url,
                    wait_until='domcontentloaded',
                    timeout=self.timeout_ms,
                )

                if not response:
                    raise PlaywrightError("Navigation failed: no response")

                # Get initial HTML
                html = page.content()

                # Detect Cloudflare challenge
                cloudflare_detected = self._has_cloudflare_challenge(html)

                # Attempt to solve CAPTCHA if detected and enabled
                if cloudflare_detected and self.solve_captcha and self.twocaptcha_api_key:
                    logger.warning(f"Cloudflare challenge detected, attempting to solve with 2Captcha...")
                    solved = self._solve_cloudflare_turnstile(page, url)
                    if solved:
                        # Refresh HTML after solving
                        html = page.content()
                        logger.info("Cloudflare challenge solved successfully")
                    else:
                        logger.error("Failed to solve Cloudflare challenge")

                # Capture diagnostics
                status_code = response.status
                final_url = page.url
                latency_ms = int((time.time() - start_time) * 1000)
                browser_version = browser.version

                # Detect Cloudflare bypass (recheck after potential solving)
                cloudflare_bypassed = self._detect_cloudflare_bypass(html)

                # Try to get exit IP if proxy was used
                proxy_exit_ip = None
                if proxy_url:
                    proxy_exit_ip = self._get_exit_ip(page)

                # Stop tracing and save artifact
                if self.record_trace and tracking_id and artifact_path:
                    try:
                        context.tracing.stop(path=artifact_path)
                        logger.info(f"Trace saved to: {artifact_path}")
                    except Exception as e:
                        logger.error(f"Failed to save trace: {e}")
                        artifact_path = None

                logger.info(
                    "BROWSER_FETCH_END url=%s proxy_id=%s status=%s final_url=%s latency_ms=%s proxy=%s cf_bypass=%s artifact=%s",
                    url,
                    proxy_id,
                    status_code,
                    final_url,
                    latency_ms,
                    bool(proxy_url),
                    cloudflare_bypassed,
                    bool(artifact_path),
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
                    cookies_used=cookies if cookies else None,
                    cloudflare_bypassed=cloudflare_bypassed,
                    artifact_path=artifact_path,
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
                cookies_used=None,
                cloudflare_bypassed=False,
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
                cookies_used=None,
                cloudflare_bypassed=False,
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

        if not parsed.hostname:
            return {"server": proxy_url}

        config = {
            "server": f"http://{parsed.hostname}:{parsed.port or 80}"
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
            exit_ip = None
            try:
                exit_ip = page.text_content("body")
            except Exception:
                # Some mocks do not support text_content(selector)
                exit_ip = page.text_content() if hasattr(page, "text_content") else None
            exit_ip = (exit_ip or page.content() or "").strip()

            # Validate IP format (simple check)
            if exit_ip and "." in exit_ip and len(exit_ip) < 16:
                return exit_ip
        except Exception as e:
            logger.warning(f"Failed to get exit IP: {e}")

        return None

    def _parse_cookies(self, url: str, cookie_string: str) -> list:
        """
        Parse cookie string into Playwright cookie format.

        Args:
            url: Target URL (for domain extraction)
            cookie_string: Cookie string (e.g., "name1=value1; name2=value2")

        Returns:
            List of Playwright cookie dicts
        """
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        domain = parsed_url.hostname

        cookies = []
        for cookie in cookie_string.split(';'):
            cookie = cookie.strip()
            if '=' not in cookie:
                continue

            name, value = cookie.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': domain,
                'path': '/',
            })

        return cookies

    def _has_cloudflare_challenge(self, html: str) -> bool:
        """
        Detect if page contains an active Cloudflare challenge.

        Args:
            html: Page HTML content

        Returns:
            True if Cloudflare challenge detected, False otherwise
        """
        html_lower = html.lower()

        # Strong indicators of active Cloudflare challenge
        challenge_indicators = [
            'checking your browser',
            'just a moment',
            'cf-chl-bypass',
            'cf-challenge-running',
            'challenge-platform',
        ]

        for indicator in challenge_indicators:
            if indicator in html_lower:
                logger.info(f"Cloudflare challenge indicator found: '{indicator}'")
                return True

        return False

    def _solve_cloudflare_turnstile(self, page: Page, url: str) -> bool:
        """
        Solve Cloudflare Turnstile challenge using 2Captcha.

        Args:
            page: Playwright page with Cloudflare challenge
            url: Current page URL

        Returns:
            True if solved successfully, False otherwise
        """
        try:
            from twocaptcha import TwoCaptcha

            # Initialize 2Captcha solver
            solver = TwoCaptcha(self.twocaptcha_api_key)

            # Extract Turnstile sitekey from page
            sitekey = self._extract_turnstile_sitekey(page)
            if not sitekey:
                logger.error("Could not extract Turnstile sitekey from page")
                return False

            logger.info(f"Extracted Turnstile sitekey: {sitekey}")

            # Submit challenge to 2Captcha
            logger.info("Submitting Turnstile challenge to 2Captcha...")
            start_time = time.time()

            result = solver.turnstile(
                sitekey=sitekey,
                url=url,
                timeout=self.cloudflare_timeout,
            )

            solve_time = int(time.time() - start_time)
            logger.info(f"2Captcha solved challenge in {solve_time}s, token: {result['code'][:30]}...")

            # Inject solution token into page
            token = result['code']
            injection_script = f"""
                // Find Turnstile response input
                const responseInput = document.querySelector('[name="cf-turnstile-response"]');
                if (responseInput) {{
                    responseInput.value = '{token}';

                    // Trigger form submission or callback
                    const form = responseInput.closest('form');
                    if (form) {{
                        form.submit();
                    }} else {{
                        // Try to trigger Turnstile callback
                        if (window.turnstile && window.turnstile.reset) {{
                            window.turnstile.reset();
                        }}
                    }}
                }}
            """

            page.evaluate(injection_script)
            logger.info("Injected 2Captcha solution token")

            # Wait for page to process solution
            time.sleep(3)
            page.wait_for_load_state('domcontentloaded', timeout=10000)

            # Check if challenge was bypassed
            new_html = page.content()
            bypassed = not self._has_cloudflare_challenge(new_html)

            if bypassed:
                logger.info("Cloudflare Turnstile challenge successfully bypassed!")
                return True
            else:
                logger.warning("Challenge still present after solving (token may have expired)")
                return False

        except ImportError:
            logger.error("2captcha-python not installed. Run: pip install 2captcha-python")
            return False

        except Exception as e:
            logger.error(f"Error solving Cloudflare Turnstile: {e}", exc_info=True)
            return False

    def _extract_turnstile_sitekey(self, page: Page) -> Optional[str]:
        """
        Extract Cloudflare Turnstile sitekey from page.

        Args:
            page: Playwright page

        Returns:
            Sitekey string, or None if not found
        """
        try:
            # Method 1: Look for data-sitekey attribute
            sitekey = page.evaluate("""
                () => {
                    const el = document.querySelector('[data-sitekey]');
                    return el ? el.getAttribute('data-sitekey') : null;
                }
            """)

            if sitekey:
                return sitekey

            # Method 2: Look in iframe src
            sitekey = page.evaluate("""
                () => {
                    const iframe = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
                    if (iframe) {
                        const match = iframe.src.match(/sitekey=([^&]+)/);
                        return match ? match[1] : null;
                    }
                    return null;
                }
            """)

            if sitekey:
                return sitekey

            # Method 3: Look in page source
            html = page.content()
            import re
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            if match:
                return match.group(1)

            return None

        except Exception as e:
            logger.error(f"Error extracting Turnstile sitekey: {e}")
            return None

    def _detect_cloudflare_bypass(self, html: str) -> bool:
        """
        Detect if Cloudflare challenge was successfully bypassed.

        Args:
            html: Page HTML content

        Returns:
            True if bypassed (no challenge detected), False if challenge present
        """
        html_lower = html.lower()

        # Cloudflare challenge indicators
        challenge_indicators = [
            'checking your browser',
            'just a moment',
            'cloudflare',
            'cf-chl',
            'cf-challenge',
            'turnstile',
            'ray id',  # Cloudflare error pages
        ]

        # Check for challenge indicators
        for indicator in challenge_indicators:
            if indicator in html_lower:
                logger.warning(f"Cloudflare challenge detected: '{indicator}' found in HTML")
                return False

        # Success indicators (page loaded normally)
        success_indicators = [
            '<title>',
            '<body',
            'bidfax',  # Site-specific
        ]

        has_success = any(indicator in html_lower for indicator in success_indicators)

        if has_success and len(html) > 5000:  # Normal page is usually >5KB
            logger.info("Cloudflare bypass successful (normal page content detected)")
            return True

        logger.warning(f"Cloudflare status unclear (HTML length: {len(html)})")
        return False
