"""Base protocol for sold results providers."""

from typing import Protocol, List, Dict, Any


class SoldResult(Dict[str, Any]):
    """
    Type hint for parsed sold result dictionaries.

    Expected keys:
    - vin: str | None
    - lot_id: str | None
    - auction_source: str (copart/iaai/unknown)
    - sale_status: str (sold/on_approval/no_sale/unknown)
    - sold_price: int | None (cents)
    - sold_at: datetime | None
    - location: str | None
    - odometer_miles: int | None
    - damage: str | None
    - condition: str | None
    - attributes: dict
    - raw_payload: dict
    - source_url: str
    """
    pass


class SoldResultsProvider(Protocol):
    """
    Protocol for sold results providers.

    Defines the interface for fetching and parsing auction sold data
    from various sources (Bidfax, Copart, IAAI, etc.).
    """

    def fetch_list_page(self, url: str) -> str:
        """
        Fetch HTML content from a list page URL.

        Args:
            url: Full URL to fetch

        Returns:
            HTML content as string

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        ...

    def parse_list_page(self, html: str, url: str) -> List[SoldResult]:
        """
        Parse list page HTML and extract sold results.

        Args:
            html: HTML content from fetch_list_page
            url: Original URL (for metadata)

        Returns:
            List of SoldResult dictionaries

        Raises:
            Exception: If parsing fails critically
        """
        ...

    def parse_detail_page(self, html: str, url: str) -> SoldResult:
        """
        Optional: Parse detail page HTML for richer data.

        Args:
            html: HTML content from detail page
            url: Detail page URL

        Returns:
            Single SoldResult dictionary

        Raises:
            Exception: If parsing fails
        """
        ...
