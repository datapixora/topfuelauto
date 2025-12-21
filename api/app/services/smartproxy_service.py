"""Smartproxy API integration for fetching proxy endpoints."""

import os
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class SmartproxyAPI:
    """Client for Smartproxy API."""

    def __init__(self, api_key: Optional[str] = None, num_proxies: int = 20):
        """
        Initialize Smartproxy API client.

        Args:
            api_key: Smartproxy API key (defaults to SMARTPROXY_API_KEY env var)
            num_proxies: Number of proxies to fetch (default: 20)
        """
        self.api_key = api_key or os.getenv("SMARTPROXY_API_KEY")
        self.base_url = "https://www.smartproxy.org/web_v1/ip/get-ip-v3"
        self.num_proxies = num_proxies

    def fetch_proxies(
        self,
        country_code: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch proxies from Smartproxy API.

        Args:
            country_code: Optional 2-letter country code (e.g., 'US', 'GB')
            state: Optional state filter
            city: Optional city filter

        Returns:
            List of proxy dictionaries with host, port, username, password, region

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API key is not configured
        """
        if not self.api_key:
            raise ValueError("Smartproxy API key not configured. Set SMARTPROXY_API_KEY environment variable.")

        try:
            # Build query parameters
            params = {
                "app_key": self.api_key,
                "pt": "9",  # Proxy type (9 = residential)
                "num": str(self.num_proxies),  # Number of proxies
                "ep": "",  # Endpoint (empty = all)
                "cc": country_code or "",  # Country code
                "state": state or "",  # State
                "city": city or "",  # City
                "life": "30",  # Proxy lifetime in minutes
                "lb": "\n",  # Line break separator
                "format": "txt",  # Text format response
                "protocol": "1",  # Protocol (1 = HTTP)
            }

            logger.info(f"Fetching {self.num_proxies} proxies from Smartproxy API...")
            response = httpx.get(self.base_url, params=params, timeout=30.0)
            response.raise_for_status()

            # Parse text response (format: username:password@host:port or host:port:username:password)
            proxy_lines = response.text.strip().split("\n")
            proxies = []

            for line in proxy_lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    proxy_dict = self._parse_proxy_line(line)
                    if proxy_dict:
                        proxies.append(proxy_dict)
                except Exception as e:
                    logger.warning(f"Failed to parse proxy line '{line}': {e}")
                    continue

            logger.info(f"Fetched and parsed {len(proxies)} proxies from Smartproxy")
            return proxies

        except httpx.HTTPStatusError as e:
            logger.error(f"Smartproxy API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Smartproxy API request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Smartproxy API unexpected error: {e}", exc_info=True)
            raise

    def _parse_proxy_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single proxy line from Smartproxy response.

        Supports multiple formats:
        - username:password@host:port
        - host:port:username:password
        - host:port (no auth)

        Args:
            line: Proxy string from Smartproxy API

        Returns:
            Dictionary with host, port, username, password, or None if invalid
        """
        # Format 1: username:password@host:port
        if "@" in line:
            auth, endpoint = line.split("@", 1)
            username, password = auth.split(":", 1)
            host, port = endpoint.rsplit(":", 1)
            return {
                "host": host,
                "port": int(port),
                "username": username,
                "password": password,
                "region": None,  # Smartproxy doesn't provide region in response
            }

        # Format 2: host:port:username:password
        parts = line.split(":")
        if len(parts) == 4:
            host, port, username, password = parts
            return {
                "host": host,
                "port": int(port),
                "username": username,
                "password": password,
                "region": None,
            }

        # Format 3: host:port (no auth)
        if len(parts) == 2:
            host, port = parts
            return {
                "host": host,
                "port": int(port),
                "username": None,
                "password": None,
                "region": None,
            }

        logger.warning(f"Unknown proxy format: {line}")
        return None

def sync_smartproxy_to_db(db, proxies: List[Dict[str, Any]], prefix: str = "Smartproxy") -> Dict[str, int]:
    """
    Sync Smartproxy API results to database.

    Creates or updates proxy endpoints based on Smartproxy data.

    Args:
        db: Database session
        proxies: List of proxy dictionaries from Smartproxy API
        prefix: Prefix for proxy names (default: "Smartproxy")

    Returns:
        Dictionary with sync statistics (created, updated, total)
    """
    from app.services import proxy_service
    from app.models.proxy_endpoint import ProxyEndpoint

    created = 0
    updated = 0
    counter = 1

    for proxy_data in proxies:
        # Extract proxy details
        host = proxy_data.get("host")
        port = proxy_data.get("port", 3128)
        username = proxy_data.get("username")
        password = proxy_data.get("password")
        region = proxy_data.get("region")

        if not host:
            logger.warning(f"Skipping proxy with no host: {proxy_data}")
            continue

        # Generate unique name
        # Since Smartproxy rotating proxies often share same host, use counter
        name = f"{prefix}-{counter:03d}"

        # Check if proxy already exists (by host+port)
        existing = db.query(ProxyEndpoint).filter(
            ProxyEndpoint.host == host,
            ProxyEndpoint.port == port,
        ).first()

        if existing:
            # Update existing proxy credentials
            proxy_service.update_proxy(db, existing.id, {
                "username": username,
                "password": password,
                "region": region,
                "is_enabled": True,  # Re-enable if it was disabled
            })
            updated += 1
        else:
            # Create new proxy
            proxy_service.create_proxy(db, {
                "name": name,
                "host": host,
                "port": port,
                "username": username,
                "password": password,
                "scheme": "http",
                "region": region,
                "is_enabled": True,
                "weight": 1,
            })
            created += 1

        counter += 1

    logger.info(f"Smartproxy sync complete: {created} created, {updated} updated")
    return {
        "created": created,
        "updated": updated,
        "total": len(proxies),
    }
