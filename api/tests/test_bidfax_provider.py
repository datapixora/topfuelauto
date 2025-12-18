import pytest
from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider
from app.schemas.auction import BidfaxTestParseRequest

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


def test_fetch_list_page_uses_proxy(monkeypatch):
    """Ensure fetch_list_page uses httpx Client with proxy when provided."""
    captured = {}

    class DummyResponse:
        text = "ok"

        def raise_for_status(self):
            return None

    class DummyClient:
        def __init__(self, proxy=None, timeout=None, follow_redirects=None):
            captured["proxy"] = proxy
            captured["timeout"] = timeout
            captured["follow_redirects"] = follow_redirects

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None):
            captured["url"] = url
            captured["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr("app.services.sold_results.providers.bidfax.httpx.Client", DummyClient)

    provider = BidfaxHtmlProvider()
    provider.fetch_list_page("https://example.com", proxy_url="http://proxy.local:3128")

    assert captured["proxy"] == "http://proxy.local:3128"
    assert captured["url"] == "https://example.com"
    assert captured["follow_redirects"] is True


def test_bidfax_test_parse_request_accepts_proxy():
    """Schema should accept optional proxy_id."""
    req = BidfaxTestParseRequest(url="https://en.bidfax.info/ford/c-max/", proxy_id=7)
    assert req.proxy_id == 7


def test_bidfax_test_parse_response_structure():
    """Test the structured response schema for test-parse endpoint."""
    from app.schemas.auction import BidfaxTestParseResponse, HttpInfo, ProxyInfo, ParseInfo, DebugInfo

    # Test successful parse response
    response = BidfaxTestParseResponse(
        ok=True,
        http=HttpInfo(
            status=200,
            error=None,
            latency_ms=523,
        ),
        proxy=ProxyInfo(
            used=True,
            proxy_id=1,
            proxy_name="SmartProxy US",
            exit_ip="123.45.67.89",
            error=None,
        ),
        parse=ParseInfo(
            ok=True,
            missing=[],
            sale_status="sold",
            final_bid=1250000,  # $12,500 in cents
            vin="1FADP5AU1FL123456",
            lot_id="67890",
            sold_at="2025-12-16T00:00:00",
        ),
        debug=DebugInfo(
            url="https://en.bidfax.info/ford/c-max/",
            provider="bidfax_html",
        ),
    )

    assert response.ok is True
    assert response.http.status == 200
    assert response.http.latency_ms == 523
    assert response.proxy.used is True
    assert response.proxy.proxy_id == 1
    assert response.proxy.exit_ip == "123.45.67.89"
    assert response.parse.ok is True
    assert response.parse.vin == "1FADP5AU1FL123456"
    assert response.parse.final_bid == 1250000
    assert response.debug.provider == "bidfax_html"

    # Test failed parse response (403 blocked)
    failed_response = BidfaxTestParseResponse(
        ok=False,
        http=HttpInfo(
            status=403,
            error="HTTP 403: Forbidden (blocked; try using a proxy)",
            latency_ms=234,
        ),
        proxy=ProxyInfo(
            used=False,
            proxy_id=None,
            proxy_name=None,
            exit_ip=None,
            error=None,
        ),
        parse=ParseInfo(
            ok=False,
            missing=[],
        ),
        debug=DebugInfo(
            url="https://en.bidfax.info/ford/c-max/",
            provider="bidfax_html",
        ),
    )

    assert failed_response.ok is False
    assert failed_response.http.status == 403
    assert "blocked" in failed_response.http.error
    assert failed_response.proxy.used is False
    assert failed_response.parse.ok is False


def test_bidfax_job_create_accepts_proxy():
    """Schema should accept optional proxy_id for job creation."""
    from app.schemas.auction import BidfaxJobCreate

    job = BidfaxJobCreate(
        target_url="https://en.bidfax.info/ford/c-max/",
        pages=5,
        make="Ford",
        model="C-Max",
        schedule_enabled=False,
        proxy_id=3,
    )

    assert job.proxy_id == 3
    assert job.target_url == "https://en.bidfax.info/ford/c-max/"
    assert job.pages == 5
