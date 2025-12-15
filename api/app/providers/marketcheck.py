import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class MarketCheckProvider:
    name = "marketcheck"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = bool(settings.marketcheck_active)
        self.api_key = settings.marketcheck_api_key
        self.api_secret = settings.marketcheck_api_secret
        self.base_url = settings.marketcheck_api_base.rstrip("/")

        if not self.enabled:
            logger.info("MarketCheck provider disabled (missing credentials or disabled flag).")

    def build_params(
        self,
        query: str,
        filters: Dict[str, Any],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        start = max(page - 1, 0) * page_size

        params: Dict[str, Any] = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "start": start,
            "rows": page_size,
        }

        # Only include q if no structured filters exist
        # When make/model are present, completely omit q parameter
        has_structured_filters = filters.get("make") or filters.get("model")
        if not has_structured_filters:
            params["q"] = query

        if filters.get("make"):
            params["make"] = filters["make"]
        if filters.get("model"):
            params["model"] = filters["model"]
        if filters.get("year_min") or filters.get("year_max"):
            y_min = filters.get("year_min") or ""
            y_max = filters.get("year_max") or ""
            params["year_range"] = f"{y_min}-{y_max}"
        if filters.get("price_min") or filters.get("price_max"):
            p_min = filters.get("price_min") or ""
            p_max = filters.get("price_max") or ""
            params["price_range"] = f"{p_min}-{p_max}"
        if filters.get("location"):
            params["car_location"] = filters["location"]
        if filters.get("sort"):
            params["sort_by"] = filters["sort"]
        return params

    def normalize_listing(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        vehicle = raw.get("build") or {}
        price = raw.get("price")
        vin = raw.get("vin") or raw.get("id") or ""
        return {
            "id": f"{self.name}:{vin or raw.get('id') or ''}",
            "title": raw.get("heading") or raw.get("title") or "Listing",
            "year": vehicle.get("year") or raw.get("year"),
            "make": vehicle.get("make") or raw.get("make"),
            "model": vehicle.get("model") or raw.get("model"),
            "trim": vehicle.get("trim"),
            "price": price,
            "currency": "USD",
            "location": raw.get("city") or raw.get("dealer_city"),
            "url": raw.get("vdp_url") or raw.get("deep_link"),
            "source": self.name,
            "risk_flags": [],
        }

    def search_listings(
        self,
        query: str,
        filters: Dict[str, Any],
        page: int,
        page_size: int,
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        if not self.enabled:
            return [], 0, {"name": self.name, "enabled": False, "message": "Provider disabled"}

        params = self.build_params(query, filters, page, page_size)
        url = f"{self.base_url}/search/car/active"
        try:
            resp = httpx.get(url, params=params, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            listings = data.get("listings") or []
            total = data.get("num_listings") or len(listings)
            normalized = [self.normalize_listing(item) for item in listings]
            return normalized, total, {"name": self.name, "enabled": True, "total": total}
        except Exception as exc:  # noqa: BLE001
            logger.warning("MarketCheck search failed: %s", exc)
            return [], 0, {"name": self.name, "enabled": True, "error": "request_failed"}
