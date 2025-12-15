"""
Test provider gating logic to ensure MarketCheck is skipped when no make/model is present.
"""
from typing import Any, Dict, Tuple


class MockMarketCheckProvider:
    """Mock MarketCheck provider with gating requirements"""
    name = "marketcheck"
    requires_structured = True
    supports_free_text = False


class MockCopartPublicProvider:
    """Mock Copart provider that works with free-text"""
    name = "copart_public"
    requires_structured = False
    supports_free_text = True


def _should_execute_provider(provider, filters: Dict[str, Any]) -> Tuple[bool, str | None]:
    """
    Determine if a provider should be executed based on filters and capabilities.

    Returns: (should_execute, skip_reason)
    """
    requires_structured = getattr(provider, "requires_structured", False)
    has_structured = filters.get("make") or filters.get("model")

    if requires_structured and not has_structured:
        return False, "requires_structured_filters"

    return True, None


def test_marketcheck_skipped_without_filters():
    """MarketCheck should be skipped when no make/model exists"""
    provider = MockMarketCheckProvider()
    filters = {"year_min": 2020, "price_max": 50000}

    should_execute, skip_reason = _should_execute_provider(provider, filters)

    assert not should_execute, "MarketCheck should be skipped without make/model"
    assert skip_reason == "requires_structured_filters", f"Expected 'requires_structured_filters', got {skip_reason}"
    print("[PASS] MarketCheck skipped without make/model")


def test_marketcheck_executes_with_make():
    """MarketCheck should execute when make is provided"""
    provider = MockMarketCheckProvider()
    filters = {"make": "nissan", "year_min": 2020}

    should_execute, skip_reason = _should_execute_provider(provider, filters)

    assert should_execute, "MarketCheck should execute with make filter"
    assert skip_reason is None, f"Expected no skip reason, got {skip_reason}"
    print("[PASS] MarketCheck executes with make filter")


def test_marketcheck_executes_with_model():
    """MarketCheck should execute when model is provided"""
    provider = MockMarketCheckProvider()
    filters = {"model": "350z", "price_max": 50000}

    should_execute, skip_reason = _should_execute_provider(provider, filters)

    assert should_execute, "MarketCheck should execute with model filter"
    assert skip_reason is None, f"Expected no skip reason, got {skip_reason}"
    print("[PASS] MarketCheck executes with model filter")


def test_marketcheck_executes_with_both():
    """MarketCheck should execute when both make and model are provided"""
    provider = MockMarketCheckProvider()
    filters = {"make": "nissan", "model": "350z"}

    should_execute, skip_reason = _should_execute_provider(provider, filters)

    assert should_execute, "MarketCheck should execute with make and model"
    assert skip_reason is None, f"Expected no skip reason, got {skip_reason}"
    print("[PASS] MarketCheck executes with make and model")


def test_copart_always_executes():
    """Copart should always execute regardless of filters"""
    provider = MockCopartPublicProvider()

    # Test with no filters
    filters = {}
    should_execute, skip_reason = _should_execute_provider(provider, filters)
    assert should_execute, "Copart should execute without filters"
    assert skip_reason is None, f"Expected no skip reason, got {skip_reason}"
    print("[PASS] Copart executes without filters")

    # Test with make/model
    filters = {"make": "nissan", "model": "350z"}
    should_execute, skip_reason = _should_execute_provider(provider, filters)
    assert should_execute, "Copart should execute with filters"
    assert skip_reason is None, f"Expected no skip reason, got {skip_reason}"
    print("[PASS] Copart executes with filters")


def test_edge_cases():
    """Test edge cases like empty strings and None values"""
    provider = MockMarketCheckProvider()

    # Empty strings should be treated as no filter
    filters = {"make": "", "model": ""}
    should_execute, skip_reason = _should_execute_provider(provider, filters)
    assert not should_execute, "MarketCheck should be skipped with empty strings"
    print("[PASS] MarketCheck skipped with empty strings")

    # None values should be treated as no filter
    filters = {"make": None, "model": None}
    should_execute, skip_reason = _should_execute_provider(provider, filters)
    assert not should_execute, "MarketCheck should be skipped with None values"
    print("[PASS] MarketCheck skipped with None values")

    # Whitespace-only strings are truthy but might be problematic
    # This test documents current behavior - might want to normalize later
    filters = {"make": "   ", "model": ""}
    should_execute, skip_reason = _should_execute_provider(provider, filters)
    assert should_execute, "Whitespace-only make is currently treated as valid (truthy)"
    print("[PASS] Whitespace-only strings are truthy (current behavior)")


if __name__ == "__main__":
    print("Testing provider gating logic...")
    print()

    try:
        test_marketcheck_skipped_without_filters()
        test_marketcheck_executes_with_make()
        test_marketcheck_executes_with_model()
        test_marketcheck_executes_with_both()
        test_copart_always_executes()
        test_edge_cases()

        print()
        print("All provider gating tests passed!")
    except AssertionError as e:
        print()
        print(f"[FAIL] Test failed: {e}")
        exit(1)
