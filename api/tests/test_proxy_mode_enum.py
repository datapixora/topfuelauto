"""
Regression test for ProxyMode enum case handling.

This test verifies that the ProxyMode enum correctly handles uppercase values
and that the Pydantic validators normalize lowercase inputs to uppercase.

Related bug: 500 error on GET /api/v1/admin/data/sources due to SQLAlchemy
Enum decode error when database contains lowercase 'none' instead of 'NONE'.
"""

import pytest
from pydantic import ValidationError

from app.models.admin_source import ProxyMode
from app.schemas.data_engine import AdminSourceCreate, AdminSourceUpdate


def test_proxy_mode_enum_values_are_uppercase():
    """Verify that ProxyMode enum values are uppercase."""
    assert ProxyMode.NONE.value == "NONE"
    assert ProxyMode.POOL.value == "POOL"
    assert ProxyMode.MANUAL.value == "MANUAL"


def test_proxy_mode_enum_by_name():
    """Verify that ProxyMode enum can be accessed by name."""
    assert ProxyMode["NONE"] == ProxyMode.NONE
    assert ProxyMode["POOL"] == ProxyMode.POOL
    assert ProxyMode["MANUAL"] == ProxyMode.MANUAL


def test_admin_source_create_normalizes_lowercase_proxy_mode():
    """Verify that AdminSourceCreate normalizes lowercase proxy_mode to uppercase."""
    data = {
        "key": "test_source",
        "name": "Test Source",
        "base_url": "https://example.com",
        "proxy_mode": "none",  # lowercase
    }
    source = AdminSourceCreate(**data)
    assert source.proxy_mode == ProxyMode.NONE


def test_admin_source_create_accepts_uppercase_proxy_mode():
    """Verify that AdminSourceCreate accepts uppercase proxy_mode."""
    data = {
        "key": "test_source",
        "name": "Test Source",
        "base_url": "https://example.com",
        "proxy_mode": "NONE",  # uppercase
    }
    source = AdminSourceCreate(**data)
    assert source.proxy_mode == ProxyMode.NONE


def test_admin_source_create_accepts_enum_value():
    """Verify that AdminSourceCreate accepts ProxyMode enum directly."""
    data = {
        "key": "test_source",
        "name": "Test Source",
        "base_url": "https://example.com",
        "proxy_mode": ProxyMode.POOL,
    }
    source = AdminSourceCreate(**data)
    assert source.proxy_mode == ProxyMode.POOL


def test_admin_source_update_normalizes_lowercase_proxy_mode():
    """Verify that AdminSourceUpdate normalizes lowercase proxy_mode to uppercase."""
    data = {"proxy_mode": "manual"}  # lowercase
    update = AdminSourceUpdate(**data)
    assert update.proxy_mode == ProxyMode.MANUAL


def test_admin_source_update_accepts_none_proxy_mode():
    """Verify that AdminSourceUpdate accepts None for proxy_mode."""
    data = {"name": "Updated Name"}
    update = AdminSourceUpdate(**data)
    assert update.proxy_mode is None


def test_proxy_mode_rejects_invalid_values():
    """Verify that invalid proxy_mode values are rejected."""
    data = {
        "key": "test_source",
        "name": "Test Source",
        "base_url": "https://example.com",
        "proxy_mode": "invalid",
    }
    with pytest.raises(ValidationError) as exc_info:
        AdminSourceCreate(**data)

    # Verify the error message mentions the invalid value
    assert "proxy_mode" in str(exc_info.value).lower()


def test_proxy_mode_mixed_case_normalization():
    """Verify that mixed case proxy_mode values are normalized correctly."""
    test_cases = [
        ("none", ProxyMode.NONE),
        ("None", ProxyMode.NONE),
        ("NONE", ProxyMode.NONE),
        ("pool", ProxyMode.POOL),
        ("Pool", ProxyMode.POOL),
        ("POOL", ProxyMode.POOL),
        ("manual", ProxyMode.MANUAL),
        ("Manual", ProxyMode.MANUAL),
        ("MANUAL", ProxyMode.MANUAL),
    ]

    for input_value, expected_enum in test_cases:
        data = {
            "key": "test_source",
            "name": "Test Source",
            "base_url": "https://example.com",
            "proxy_mode": input_value,
        }
        source = AdminSourceCreate(**data)
        assert source.proxy_mode == expected_enum, f"Failed for input: {input_value}"
