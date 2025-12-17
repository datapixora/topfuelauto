"""
Test CopartPublicProvider resilience to non-JSON responses and HTTP errors.
"""
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.copart_public import CopartPublicProvider


def test_non_json_response_html():
    """Test handling of HTML response (Cloudflare block page)"""
    provider = CopartPublicProvider()

    # Mock response with HTML content
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = "<html><body>Access Denied - Cloudflare</body></html>"

    with patch("httpx.get", return_value=mock_response):
        items, total, meta = provider.search_listings(
            query="ford mustang",
            filters={},
            page=1,
            page_size=10,
        )

    assert items == [], "Should return empty items"
    assert total == 0, "Should return zero total"
    assert meta["name"] == "copart_public", "Should include provider name"
    assert meta["error"] == "non_json_response", "Should indicate non-JSON response"
    print("[PASS] HTML response handled gracefully")


def test_403_forbidden():
    """Test handling of 403 Forbidden response"""
    provider = CopartPublicProvider()

    # Mock 403 response
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = "Forbidden"

    with patch("httpx.get", return_value=mock_response):
        items, total, meta = provider.search_listings(
            query="ford mustang",
            filters={},
            page=1,
            page_size=10,
        )

    assert items == [], "Should return empty items"
    assert total == 0, "Should return zero total"
    assert meta["error"] == "http_error_403", "Should indicate 403 error"
    print("[PASS] 403 Forbidden handled gracefully")


def test_empty_response():
    """Test handling of empty response body"""
    provider = CopartPublicProvider()

    # Mock empty response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.text = ""

    with patch("httpx.get", return_value=mock_response):
        items, total, meta = provider.search_listings(
            query="ford mustang",
            filters={},
            page=1,
            page_size=10,
        )

    assert items == [], "Should return empty items"
    assert total == 0, "Should return zero total"
    assert meta["error"] == "non_json_response", "Should indicate non-JSON response"
    print("[PASS] Empty response handled gracefully")


def test_valid_json_response():
    """Test handling of valid JSON response"""
    provider = CopartPublicProvider()

    # Mock valid JSON response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = json.dumps({
        "data": {
            "results": [],
            "totalElements": 0,
        }
    })
    mock_response.json.return_value = {
        "data": {
            "results": [],
            "totalElements": 0,
        }
    }

    with patch("httpx.get", return_value=mock_response):
        items, total, meta = provider.search_listings(
            query="ford mustang",
            filters={},
            page=1,
            page_size=10,
        )

    assert items == [], "Should return items from response"
    assert total == 0, "Should return total from response"
    assert "error" not in meta, "Should not have error in meta"
    assert meta["enabled"] is True, "Should be enabled"
    print("[PASS] Valid JSON response processed correctly")


def test_timeout_exception():
    """Test handling of timeout exception"""
    provider = CopartPublicProvider()

    # Mock timeout exception
    import httpx
    with patch("httpx.get", side_effect=httpx.TimeoutException("Request timeout")):
        items, total, meta = provider.search_listings(
            query="ford mustang",
            filters={},
            page=1,
            page_size=10,
        )

    assert items == [], "Should return empty items on timeout"
    assert total == 0, "Should return zero total on timeout"
    assert meta["error"] == "timeout", "Should indicate timeout error"
    print("[PASS] Timeout exception handled gracefully")


def test_json_decode_error():
    """Test handling of JSONDecodeError (malformed JSON)"""
    provider = CopartPublicProvider()

    # Mock response with malformed JSON
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = "{invalid json}"
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "{invalid json}", 0)

    with patch("httpx.get", return_value=mock_response):
        items, total, meta = provider.search_listings(
            query="ford mustang",
            filters={},
            page=1,
            page_size=10,
        )

    assert items == [], "Should return empty items on JSON decode error"
    assert total == 0, "Should return zero total on JSON decode error"
    assert meta["error"] == "request_failed", "Should indicate request failed"
    print("[PASS] JSONDecodeError handled gracefully")


if __name__ == "__main__":
    print("Testing CopartPublicProvider resilience...")
    print()

    try:
        test_non_json_response_html()
        test_403_forbidden()
        test_empty_response()
        test_valid_json_response()
        test_timeout_exception()
        test_json_decode_error()

        print()
        print("All Copart resilience tests passed!")
    except AssertionError as e:
        print()
        print(f"[FAIL] Test failed: {e}")
        exit(1)
