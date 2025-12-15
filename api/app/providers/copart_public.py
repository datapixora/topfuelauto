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
        max_retries = 1

        for attempt in range(max_retries + 1):
            try:
                resp = httpx.get(self.base_url, params=params, headers=self.headers, timeout=10.0)

                # Capture response metadata for logging
                status_code = resp.status_code
                content_type = resp.headers.get("content-type", "")
                response_snippet = resp.text[:300] if resp.text else ""

                # Check if response is valid JSON before parsing
                if status_code != 200:
                    logger.warning(
                        "CopartPublicProvider non-200 status: provider=%s status=%s content_type=%s snippet=%s",
                        self.name,
                        status_code,
                        content_type,
                        response_snippet,
                    )
                    if attempt < max_retries:
                        continue
                    return [], 0, {
                        "name": self.name,
                        "enabled": True,
                        "error": f"http_error_{status_code}",
                    }

                # Verify content is JSON before parsing
                is_json_content_type = "application/json" in content_type.lower()
                body_starts_with_json = response_snippet.strip().startswith(("{", "["))

                if not (is_json_content_type or body_starts_with_json):
                    logger.warning(
                        "CopartPublicProvider non-JSON response: provider=%s status=%s content_type=%s snippet=%s",
                        self.name,
                        status_code,
                        content_type,
                        response_snippet,
                    )
                    if attempt < max_retries:
                        continue
                    return [], 0, {
                        "name": self.name,
                        "enabled": True,
                        "error": "non_json_response",
                    }

                # Safe to parse JSON
                data = resp.json()
                results = data.get("data", {}).get("results") or []
                normalized = [self.normalize_listing(item) for item in results]
                total = data.get("data", {}).get("totalElements") or len(results)
                return normalized, total, {"name": self.name, "enabled": True, "total": total}

            except httpx.TimeoutException as exc:
                logger.warning(
                    "CopartPublicProvider timeout: provider=%s attempt=%s/%s error=%s",
                    self.name,
                    attempt + 1,
                    max_retries + 1,
                    str(exc),
                )
                if attempt < max_retries:
                    continue
                return [], 0, {"name": self.name, "enabled": True, "error": "timeout"}
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "CopartPublicProvider search failed: provider=%s attempt=%s/%s error=%s",
                    self.name,
                    attempt + 1,
                    max_retries + 1,
                    str(exc),
                )
                if attempt < max_retries:
                    continue
                return [], 0, {"name": self.name, "enabled": True, "error": "request_failed"}

        # Fallback (should not reach here)
        return [], 0, {"name": self.name, "enabled": True, "error": "unknown"}
