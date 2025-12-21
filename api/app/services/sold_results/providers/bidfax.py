"""Bidfax HTML scraping provider with multiple fetch modes."""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from ..fetch_diagnostics import FetchDiagnostics
from ..fetchers import HttpFetcher, BrowserFetcher

logger = logging.getLogger(__name__)


class BidfaxHtmlProvider:
    """
    Bidfax HTML scraping provider.

    Fetches and parses Bidfax sold results pages using BeautifulSoup.
    Supports both HTTP and browser-based fetching for flexibility.
    """

    def __init__(
        self,
        rate_limit_per_minute: int = 30,
        watch_mode: bool = False,
        use_2captcha: bool = False,
    ):
        """
        Initialize provider with fetchers.

        Args:
            rate_limit_per_minute: Maximum requests per minute for HTTP mode (default: 30)
            watch_mode: Enable visual browser mode (headless=False) for local debugging (default: False)
            use_2captcha: Enable 2Captcha for challenge solving (default: False)
        """
        self.http_fetcher = HttpFetcher(rate_limit_per_minute=rate_limit_per_minute)

        # Determine headless mode - watch_mode overrides to show browser
        headless = not watch_mode
        # Increase timeout if using 2Captcha (solving takes time)
        timeout_ms = 60000 if use_2captcha else 30000
        # Add slow_mo for watch mode (makes actions visible)
        slow_mo = 150 if watch_mode else 0
        # Enable trace recording in production
        record_trace = True  # Always record for debugging

        self.browser_fetcher = BrowserFetcher(
            headless=headless,
            timeout_ms=timeout_ms,
            solve_captcha=use_2captcha,
            slow_mo=slow_mo,
            record_trace=record_trace,
        )

    def fetch_list_page(
        self,
        url: str,
        proxy_url: Optional[str] = None,
        fetch_mode: str = "http",
        timeout: float = 10.0,
        cookies: Optional[str] = None,
        tracking_id: Optional[int] = None,
    ) -> FetchDiagnostics:
        """
        Fetch HTML from list page using specified fetch mode.

        Args:
            url: Bidfax list page URL
            proxy_url: Optional proxy URL
            fetch_mode: Fetch mode to use ("http" or "browser")
            timeout: Request timeout in seconds (HTTP mode only)
            cookies: Optional cookie string (browser mode only)
            tracking_id: Optional tracking ID for artifact naming (browser mode only)

        Returns:
            FetchDiagnostics with HTML and metadata

        Raises:
            ValueError: If fetch_mode is invalid
        """
        if fetch_mode == "http":
            return self.http_fetcher.fetch(url, proxy_url=proxy_url, timeout=timeout)
        elif fetch_mode == "browser":
            return self.browser_fetcher.fetch(
                url,
                proxy_url=proxy_url,
                cookies=cookies,
                tracking_id=tracking_id,
            )
        else:
            raise ValueError(f"Invalid fetch_mode: {fetch_mode}. Must be 'http' or 'browser'.")

    def parse_list_page(self, html: str, url: str) -> List[Dict[str, Any]]:
        """
        Parse Bidfax list page HTML and extract sold results.

        Bidfax structure:
        - Cards: div.thumbnail.offer
        - Price: span.prices
        - VIN: h2 title (regex extraction)
        - Lot: "Lot number:" label + span.blackfont
        - Source: span.copart or span.iaai
        - Status: img[alt] (Sold/On approval/No sale)
        - Date: "Date of sale:" + DD.MM.YYYY
        - Odometer: text with "miles"
        - Damage/Condition/Location: label + span.blackfont

        Args:
            html: HTML content from fetch_list_page
            url: Source URL for metadata

        Returns:
            List of parsed sold result dictionaries
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # Find all offer cards
        cards = soup.select('div.thumbnail.offer')
        logger.info(f"Found {len(cards)} offer cards on {url}")

        for card in cards:
            try:
                result = self._parse_card(card, url)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to parse card: {e}", exc_info=True)
                continue

        return results

    def _parse_card(self, card, source_url: str) -> Optional[Dict[str, Any]]:
        """
        Parse individual offer card from Bidfax.

        Args:
            card: BeautifulSoup element (div.thumbnail.offer)
            source_url: Original list page URL

        Returns:
            Dictionary with extracted fields, or None if critical data missing
        """
        result: Dict[str, Any] = {
            "source_url": source_url,
            "auction_source": "unknown",
            "sale_status": "unknown",
            "currency": "USD",
        }

        # Extract VIN from title (h2)
        title_elem = card.select_one('h2')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            result["title"] = title_text

            # Regex: VIN:\s*([A-HJ-NPR-Z0-9]{17})
            # VIN format excludes I, O, Q to avoid confusion with 1, 0
            vin_match = re.search(r'VIN:\s*([A-HJ-NPR-Z0-9]{17})', title_text, re.IGNORECASE)
            if vin_match:
                result["vin"] = vin_match.group(1).upper()

        # Extract sold price from span.prices
        price_elem = card.select_one('span.prices')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            result["sold_price"] = self._parse_price(price_text)

        # Extract detail URL from .img-wrapper a[href]
        detail_link = card.select_one('.img-wrapper a[href]')
        if detail_link:
            result["detail_url"] = detail_link.get('href')

        # Extract lot number
        lot_span = card.find('span', string=re.compile(r'Lot number:', re.IGNORECASE))
        if lot_span:
            lot_black = lot_span.find_next('span', class_='blackfont')
            if lot_black:
                result["lot_id"] = lot_black.get_text(strip=True)

        # Extract auction source (copart/iaai)
        if card.select_one('span.copart'):
            result["auction_source"] = "copart"
        elif card.select_one('span.iaai'):
            result["auction_source"] = "iaai"

        # Extract status from img alt attribute
        status_img = card.select_one('img[alt]')
        if status_img:
            alt_text = status_img.get('alt', '').lower()
            if 'sold' in alt_text:
                result["sale_status"] = "sold"
            elif 'approval' in alt_text:
                result["sale_status"] = "on_approval"
            elif 'no sale' in alt_text or 'nosale' in alt_text:
                result["sale_status"] = "no_sale"

        # Extract date of sale (DD.MM.YYYY format)
        date_span = card.find('span', string=re.compile(r'Date of sale:', re.IGNORECASE))
        if date_span:
            # Get parent element text to find date after label
            date_text = date_span.parent.get_text(strip=True) if date_span.parent else date_span.get_text(strip=True)
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_text)
            if date_match:
                result["sold_at"] = self._parse_date(date_match.group(1))

        # Extract odometer/mileage (e.g., "178424 miles")
        odometer_text = card.find(string=re.compile(r'\d+\s*miles', re.IGNORECASE))
        if odometer_text:
            result["odometer_miles"] = self._parse_odometer(str(odometer_text))

        # Extract damage
        damage_span = card.find('span', string=re.compile(r'Damage:', re.IGNORECASE))
        if damage_span:
            damage_value = damage_span.find_next('span', class_='blackfont')
            if damage_value:
                result["damage"] = damage_value.get_text(strip=True)

        # Extract condition
        condition_span = card.find('span', string=re.compile(r'Condition:', re.IGNORECASE))
        if condition_span:
            condition_value = condition_span.find_next('span', class_='blackfont')
            if condition_value:
                result["condition"] = condition_value.get_text(strip=True)

        # Extract location
        location_span = card.find('span', string=re.compile(r'Location:', re.IGNORECASE))
        if location_span:
            location_value = location_span.find_next('span', class_='blackfont')
            if location_value:
                result["location"] = location_value.get_text(strip=True)

        # Store raw card HTML for debugging (first 500 chars)
        result["raw_payload"] = {
            "html_snippet": str(card)[:500],
            "parsed_at": datetime.utcnow().isoformat(),
        }

        # Store additional attributes in attributes dict
        result["attributes"] = {}

        return result

    def _parse_price(self, text: str) -> Optional[int]:
        """
        Parse price from text like '$12,500' to cents.

        Args:
            text: Price string (e.g., "$12,500", "£10,000")

        Returns:
            Price in cents (int), or None if parsing fails
        """
        # Remove all non-digit characters
        cleaned = re.sub(r'[^\d]', '', text)
        if not cleaned:
            return None

        try:
            # Convert dollars to cents
            return int(cleaned) * 100
        except ValueError:
            return None

    def _parse_odometer(self, text: str) -> Optional[int]:
        """
        Parse odometer from text like '178424 miles' or '59,293 A'.

        Args:
            text: Odometer string

        Returns:
            Mileage as integer, or None if parsing fails
        """
        # Extract first number sequence (with optional commas)
        match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)', text)
        if match:
            cleaned = match.group(1).replace(',', '')
            try:
                miles = int(cleaned)
                # Sanity check (reject obviously invalid values)
                if miles > 0 and miles < 1_000_000:
                    return miles
            except ValueError:
                pass
        return None

    def _parse_date(self, text: str) -> Optional[datetime]:
        """
        Parse date from DD.MM.YYYY format.

        Args:
            text: Date string (e.g., "16.12.2025")

        Returns:
            datetime object, or None if parsing fails
        """
        try:
            return datetime.strptime(text, '%d.%m.%Y')
        except ValueError:
            return None
