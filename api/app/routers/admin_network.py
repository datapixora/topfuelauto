"""Admin API endpoints for network utilities."""

from fastapi import APIRouter, Depends
import httpx
import logging

from app.core.security import get_current_admin
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin/network", tags=["admin", "network"])
logger = logging.getLogger(__name__)


@router.get("/my-ip", response_model=dict)
def get_my_ip(admin: User = Depends(get_current_admin)):
    """
    Get server's outbound IP address.

    Useful for whitelisting the server IP with proxy providers like Smartproxy.

    Returns:
        Dictionary with ip address

    Example response:
        {"ip": "203.0.113.45"}
    """
    try:
        # Use multiple services for reliability
        services = [
            "https://api.ipify.org?format=json",
            "https://api64.ipify.org?format=json",
            "https://ifconfig.me/ip",
        ]

        for service_url in services:
            try:
                response = httpx.get(service_url, timeout=10.0)
                response.raise_for_status()

                # Parse response
                if "ipify" in service_url:
                    data = response.json()
                    return {"ip": data["ip"]}
                else:
                    # ifconfig.me returns plain text
                    return {"ip": response.text.strip()}

            except Exception as e:
                logger.warning(f"Failed to get IP from {service_url}: {e}")
                continue

        # If all services failed
        return {"ip": None, "error": "Failed to detect outbound IP"}

    except Exception as e:
        logger.error(f"Error getting outbound IP: {e}", exc_info=True)
        return {"ip": None, "error": str(e)}
