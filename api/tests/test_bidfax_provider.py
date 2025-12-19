import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.sold_results.providers.bidfax import BidfaxHtmlProvider
from app.services.sold_results.fetchers.browser_fetcher import BrowserFetcher
from app.services.sold_results.fetchers.http_fetcher import HttpFetcher
from app.services.sold_results.fetch_diagnostics import FetchDiagnostics
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


# ============================================================================
# Browser Fetcher Tests
# ============================================================================

def test_browser_fetcher_initialization():
    """Test BrowserFetcher initialization with default parameters."""
    fetcher = BrowserFetcher()
    assert fetcher.headless is True
    assert fetcher.timeout_ms == 30000

    fetcher_custom = BrowserFetcher(headless=False, timeout_ms=60000)
    assert fetcher_custom.headless is False
    assert fetcher_custom.timeout_ms == 60000


def test_browser_fetcher_parse_proxy_url():
    """Test proxy URL parsing into Playwright format."""
    fetcher = BrowserFetcher()

    # Test proxy with auth
    result = fetcher._parse_proxy_url("http://user:pass@proxy.local:3128")
    assert result["server"] == "http://proxy.local:3128"
    assert result["username"] == "user"
    assert result["password"] == "pass"

    # Test proxy without auth
    result_no_auth = fetcher._parse_proxy_url("http://proxy.local:8080")
    assert result_no_auth["server"] == "http://proxy.local:8080"
    assert "username" not in result_no_auth
    assert "password" not in result_no_auth

    # Test HTTPS proxy
    result_https = fetcher._parse_proxy_url("https://admin:secret@secure.proxy:443")
    assert result_https["server"] == "http://secure.proxy:443"
    assert result_https["username"] == "admin"
    assert result_https["password"] == "secret"


def test_browser_fetcher_fetch_success(monkeypatch):
    """Test successful browser fetch with mocked Playwright."""
    # Mock Playwright components
    mock_response = Mock()
    mock_response.status = 200

    mock_page = Mock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html><body>Test Content</body></html>"
    mock_page.url = "https://en.bidfax.info/ford/c-max/"

    mock_context = Mock()
    mock_context.new_page.return_value = mock_page

    mock_browser = Mock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.version = "120.0.6099.0"

    mock_chromium = Mock()
    mock_chromium.launch.return_value = mock_browser

    mock_playwright = MagicMock()
    mock_playwright.__enter__.return_value.chromium = mock_chromium

    # Patch sync_playwright
    with patch('app.services.sold_results.fetchers.browser_fetcher.sync_playwright', return_value=mock_playwright):
        fetcher = BrowserFetcher()
        result = fetcher.fetch("https://en.bidfax.info/ford/c-max/")

    # Assertions
    assert isinstance(result, FetchDiagnostics)
    assert result.html == "<html><body>Test Content</body></html>"
    assert result.status_code == 200
    assert result.fetch_mode == "browser"
    assert result.final_url == "https://en.bidfax.info/ford/c-max/"
    assert result.browser_version == "120.0.6099.0"
    assert result.latency_ms >= 0
    assert result.error is None


def test_browser_fetcher_fetch_with_proxy(monkeypatch):
    """Test browser fetch with proxy configuration."""
    mock_response = Mock()
    mock_response.status = 200

    mock_page = Mock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html>Content</html>"
    mock_page.url = "https://example.com"
    # Mock exit IP detection
    mock_page.text_content.return_value = "123.45.67.89"

    mock_context = Mock()
    mock_context.new_page.return_value = mock_page

    mock_browser = Mock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.version = "120.0.0"

    captured_proxy_config = {}

    def capture_context(*args, **kwargs):
        if 'proxy' in kwargs:
            captured_proxy_config.update(kwargs['proxy'])
        return mock_context

    mock_browser.new_context.side_effect = capture_context

    mock_chromium = Mock()
    mock_chromium.launch.return_value = mock_browser

    mock_playwright = MagicMock()
    mock_playwright.__enter__.return_value.chromium = mock_chromium

    with patch('app.services.sold_results.fetchers.browser_fetcher.sync_playwright', return_value=mock_playwright):
        fetcher = BrowserFetcher()
        result = fetcher.fetch("https://example.com", proxy_url="http://user:pass@proxy.local:3128")

    # Verify proxy was configured
    assert captured_proxy_config["server"] == "http://proxy.local:3128"
    assert captured_proxy_config["username"] == "user"
    assert captured_proxy_config["password"] == "pass"

    # Verify result
    assert result.status_code == 200
    assert result.proxy_exit_ip == "123.45.67.89"


def test_browser_fetcher_handles_navigation_error(monkeypatch):
    """Test browser fetcher handles navigation errors gracefully."""
    mock_page = Mock()
    mock_page.goto.side_effect = Exception("Navigation timeout")

    mock_context = Mock()
    mock_context.new_page.return_value = mock_page

    mock_browser = Mock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.version = "120.0.0"

    mock_chromium = Mock()
    mock_chromium.launch.return_value = mock_browser

    mock_playwright = MagicMock()
    mock_playwright.__enter__.return_value.chromium = mock_chromium

    with patch('app.services.sold_results.fetchers.browser_fetcher.sync_playwright', return_value=mock_playwright):
        fetcher = BrowserFetcher()
        result = fetcher.fetch("https://example.com")

    # Should return FetchDiagnostics with error
    assert isinstance(result, FetchDiagnostics)
    assert result.html == ""
    assert result.status_code == 0
    assert result.error is not None
    assert "Navigation timeout" in result.error


def test_http_fetcher_returns_fetch_diagnostics():
    """Test HttpFetcher returns FetchDiagnostics structure."""
    # This is a minimal test to ensure HttpFetcher interface matches BrowserFetcher
    fetcher = HttpFetcher(rate_limit_per_minute=60)
    # We won't actually make HTTP requests, just verify the class exists and has the right interface
    assert hasattr(fetcher, 'fetch')
    assert fetcher.rate_limit == 60


def test_bidfax_provider_fetch_mode_selection():
    """Test BidfaxHtmlProvider selects correct fetcher based on fetch_mode."""
    provider = BidfaxHtmlProvider()

    # Verify both fetchers are initialized
    assert isinstance(provider.http_fetcher, HttpFetcher)
    assert isinstance(provider.browser_fetcher, BrowserFetcher)

    # Test invalid fetch_mode raises ValueError
    with pytest.raises(ValueError, match="Invalid fetch_mode"):
        provider.fetch_list_page("https://example.com", fetch_mode="invalid_mode")


def test_fetch_diagnostics_structure():
    """Test FetchDiagnostics dataclass structure."""
    diag = FetchDiagnostics(
        html="<html>Test</html>",
        status_code=200,
        latency_ms=500,
        fetch_mode="http",
        final_url="https://example.com",
        error=None,
        proxy_exit_ip="123.45.67.89",
        browser_version="120.0.0"
    )

    assert diag.html == "<html>Test</html>"
    assert diag.status_code == 200
    assert diag.latency_ms == 500
    assert diag.fetch_mode == "http"
    assert diag.final_url == "https://example.com"
    assert diag.proxy_exit_ip == "123.45.67.89"
    assert diag.browser_version == "120.0.0"


def test_fetch_mode_defaults():
    """Test fetch_mode defaults in schemas."""
    from app.schemas.auction import BidfaxJobCreate, BidfaxTestParseRequest, DebugInfo

    # BidfaxJobCreate should default to "http"
    job = BidfaxJobCreate(
        target_url="https://en.bidfax.info/ford/c-max/",
        pages=1
    )
    assert job.fetch_mode == "http"

    # BidfaxTestParseRequest should default to "http"
    test_req = BidfaxTestParseRequest(url="https://en.bidfax.info/ford/c-max/")
    assert test_req.fetch_mode == "http"

    # DebugInfo should default to "http"
    debug = DebugInfo(url="https://example.com")
    assert debug.fetch_mode == "http"


def test_fetch_mode_browser_option():
    """Test fetch_mode can be set to 'browser'."""
    from app.schemas.auction import BidfaxJobCreate, BidfaxTestParseRequest

    # BidfaxJobCreate with browser mode
    job = BidfaxJobCreate(
        target_url="https://en.bidfax.info/ford/c-max/",
        pages=1,
        fetch_mode="browser"
    )
    assert job.fetch_mode == "browser"

    # BidfaxTestParseRequest with browser mode
    test_req = BidfaxTestParseRequest(
        url="https://en.bidfax.info/ford/c-max/",
        fetch_mode="browser"
    )
    assert test_req.fetch_mode == "browser"
