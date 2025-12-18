import pytest
from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider

# Fixture: Sample Bidfax HTML snippet
SAMPLE_HTML = """
<div class="thumbnail offer">
    <div class="img-wrapper">
        <a href="/lot/12345">
            <img src="..." alt="Sold">
        </a>
    </div>
    <h2>2015 FORD C-MAX VIN: 1FADP5AU1FL123456</h2>
    <span class="prices">$12,500</span>
    <span class="copart"></span>
    <div>
        <span>Lot number:</span> <span class="blackfont">67890</span>
    </div>
    <div>
        <span>Date of sale:</span> 16.12.2025
    </div>
    <div>178424 miles</div>
    <div><span>Damage:</span> <span class="blackfont">Front End</span></div>
    <div><span>Condition:</span> <span class="blackfont">Run and Drive</span></div>
    <div><span>Location:</span> <span class="blackfont">CA - Los Angeles</span></div>
</div>
"""


def test_parse_list_page():
    """Test BidfaxHtmlProvider.parse_list_page with sample HTML."""
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page(SAMPLE_HTML, "https://en.bidfax.info/ford/c-max/")

    assert len(results) == 1

    result = results[0]
    assert result["vin"] == "1FADP5AU1FL123456"
    assert result["lot_id"] == "67890"
    assert result["sold_price"] == 1250000  # $12,500 in cents
    assert result["auction_source"] == "copart"
    assert result["sale_status"] == "sold"
    assert result["odometer_miles"] == 178424
    assert result["damage"] == "Front End"
    assert result["condition"] == "Run and Drive"
    assert result["location"] == "CA - Los Angeles"
    assert "sold_at" in result


def test_parse_list_page_multiple_cards():
    """Test parsing multiple offer cards."""
    multi_html = SAMPLE_HTML + SAMPLE_HTML.replace("123456", "654321").replace("67890", "09876")
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page(multi_html, "https://en.bidfax.info/ford/c-max/")

    assert len(results) == 2
    assert results[0]["vin"] == "1FADP5AU1FL123456"
    assert results[1]["vin"] == "1FADP5AU1FL654321"


def test_parse_list_page_iaai_source():
    """Test parsing IAAI auction source."""
    iaai_html = SAMPLE_HTML.replace('<span class="copart"></span>', '<span class="iaai"></span>')
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page(iaai_html, "https://en.bidfax.info/ford/c-max/")

    assert len(results) == 1
    assert results[0]["auction_source"] == "iaai"


def test_parse_list_page_on_approval_status():
    """Test parsing 'on approval' sale status."""
    approval_html = SAMPLE_HTML.replace('alt="Sold"', 'alt="On approval"')
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page(approval_html, "https://en.bidfax.info/ford/c-max/")

    assert len(results) == 1
    assert results[0]["sale_status"] == "on_approval"


def test_parse_list_page_no_sale_status():
    """Test parsing 'no sale' status."""
    no_sale_html = SAMPLE_HTML.replace('alt="Sold"', 'alt="No sale"')
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page(no_sale_html, "https://en.bidfax.info/ford/c-max/")

    assert len(results) == 1
    assert results[0]["sale_status"] == "no_sale"


def test_parse_price():
    """Test price parsing."""
    provider = BidfaxHtmlProvider()
    assert provider._parse_price("$12,500") == 1250000
    assert provider._parse_price("$1,234") == 123400
    assert provider._parse_price("$50") == 5000
    assert provider._parse_price("N/A") is None
    assert provider._parse_price("") is None


def test_parse_odometer():
    """Test odometer parsing."""
    provider = BidfaxHtmlProvider()
    assert provider._parse_odometer("178424 miles") == 178424
    assert provider._parse_odometer("59,293 miles") == 59293
    assert provider._parse_odometer("100 miles") == 100
    assert provider._parse_odometer("N/A") is None
    assert provider._parse_odometer("unknown") is None


def test_parse_date():
    """Test date parsing."""
    provider = BidfaxHtmlProvider()
    result = provider._parse_date("16.12.2025")
    assert result.year == 2025
    assert result.month == 12
    assert result.day == 16

    result2 = provider._parse_date("01.01.2024")
    assert result2.year == 2024
    assert result2.month == 1
    assert result2.day == 1

    # Invalid date should return None
    assert provider._parse_date("invalid") is None
    assert provider._parse_date("32.13.2025") is None


def test_parse_list_page_missing_fields():
    """Test parsing with missing optional fields."""
    minimal_html = """
    <div class="thumbnail offer">
        <h2>2015 FORD C-MAX VIN: 1FADP5AU1FL123456</h2>
        <span class="prices">$12,500</span>
    </div>
    """
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page(minimal_html, "https://en.bidfax.info/ford/c-max/")

    assert len(results) == 1
    result = results[0]
    assert result["vin"] == "1FADP5AU1FL123456"
    assert result["sold_price"] == 1250000
    # Optional fields should be None or default
    assert result["auction_source"] == "unknown"
    assert result["sale_status"] == "unknown"


def test_parse_list_page_no_vin():
    """Test parsing card without VIN in title."""
    no_vin_html = """
    <div class="thumbnail offer">
        <h2>2015 FORD C-MAX</h2>
        <span class="prices">$12,500</span>
        <div><span>Lot number:</span> <span class="blackfont">67890</span></div>
    </div>
    """
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page(no_vin_html, "https://en.bidfax.info/ford/c-max/")

    assert len(results) == 1
    result = results[0]
    assert "vin" not in result or result["vin"] is None
    assert result["lot_id"] == "67890"


def test_parse_list_page_empty_html():
    """Test parsing empty or invalid HTML."""
    provider = BidfaxHtmlProvider()
    results = provider.parse_list_page("", "https://en.bidfax.info/ford/c-max/")
    assert len(results) == 0

    results = provider.parse_list_page("<html><body></body></html>", "https://en.bidfax.info/ford/c-max/")
    assert len(results) == 0
