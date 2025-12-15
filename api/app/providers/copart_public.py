import logging
from typing import Any, Dict, List, Tuple

import httpx

logger = logging.getLogger(__name__)


class CopartPublicProvider:
    name = "copart_public"
    requires_structured = False  # Can work with free-text
    supports_free_text = True  # Handles free-form queries

    def __init__(self):
        self.base_url = "https://www.copart.com/public/data/lotsearch/lotsearch"
        self.enabled = True
        self.headers = {
            "User-Agent": "TopFuelAuto/1.0 (+https://topfuelauto.com)",
            "Accept": "application/json",
        }

    def build_params(self, query: str, page: int, page_size: int) -> Dict[str, Any]:
        return {
            "freeFormSearch": query,
            "page": max(page - 1, 0),
            "size": page_size,
        }

    def normalize_listing(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        lot_id = raw.get("lotNumberStr") or raw.get("lotNumber")
        year = raw.get("year")
        make = raw.get("make")
        model = raw.get("model")
        title = raw.get("lotTitle") or " ".join([str(x) for x in [year, make, model] if x]) or "Copart Lot"
        location = raw.get("locationName") or raw.get("facilityName")
        price = raw.get("currentBid")
        url = f"https://www.copart.com/lot/{lot_id}" if lot_id else None
        return {
            "id": f"{self.name}:{lot_id}" if lot_id else f"{self.name}:unknown",
            "listing_id": f"{self.name}:{lot_id}" if lot_id else None,
            "title": title,
            "year": year,
            "make": make,
            "model": model,
            "price": price,
            "currency": "USD",
            "location": location,
            "url": url,
            "source": self.name,
            "risk_flags": [],
            "auction_date": raw.get("auctionDate"),
            "image_url": raw.get("imageUrl") or raw.get("thumbnailImage"),
        }

    def search_listings(
        self,
        query: str,
        filters: Dict[str, Any],
        page: int,
        page_size: int,
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        params = self.build_params(query, page, page_size)
        try:
            resp = httpx.get(self.base_url, params=params, headers=self.headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get("results") or []
            normalized = [self.normalize_listing(item) for item in results]
            total = data.get("data", {}).get("totalElements") or len(results)
            return normalized, total, {"name": self.name, "enabled": True, "total": total}
        except Exception as exc:  # noqa: BLE001
            logger.warning("CopartPublicProvider search failed: %s", exc)
            return [], 0, {"name": self.name, "enabled": True, "error": "request_failed"}
