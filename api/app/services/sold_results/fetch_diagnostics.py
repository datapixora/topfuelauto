"""Normalized fetch diagnostics for HTTP and browser fetchers."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FetchDiagnostics:
    """
    Normalized fetch result container.

    Used by both HTTP and browser fetchers to return consistent diagnostics
    alongside HTML content.
    """
    html: str
    """Fetched HTML content"""

    status_code: int
    """HTTP status code (200, 403, etc.)"""

    latency_ms: int
    """Request latency in milliseconds"""

    fetch_mode: str
    """Fetch mode used: 'http' or 'browser'"""

    final_url: str
    """Final URL after redirects"""

    error: Optional[str] = None
    """Error message if fetch failed"""

    proxy_exit_ip: Optional[str] = None
    """Exit IP if proxy was used"""

    browser_version: Optional[str] = None
    """Browser version string (for browser mode only)"""

    cookies_used: Optional[str] = None
    """Cookies used in request (for verification)"""

    cloudflare_bypassed: bool = False
    """Whether Cloudflare challenge was bypassed"""

    artifact_path: Optional[str] = None
    """Path to saved trace/video artifact (for production debugging)"""

    attempts: list = None
    """List of attempt metadata dictionaries (optional)"""
