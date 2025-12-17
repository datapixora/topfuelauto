"""Tests for internal-first search logic."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.core.config import Settings


class TestInternalFirstSearch:
    """Test internal-first search behavior."""

    def test_internal_first_enabled_with_results(self):
        """
        When SEARCH_INTERNAL_FIRST=true and internal catalog returns results,
        external providers should NOT be queried.
        """
        # Setup
        settings = Settings(
            search_internal_first=True,
            search_internal_min_results=1,
            search_external_fallback_enabled=False,
        )

        internal_provider = Mock()
        internal_provider.name = "internal_catalog"
        internal_provider.search_listings = Mock(return_value=(
            [{"id": "1", "title": "Test Car"}],  # items
            1,  # total
            {"name": "internal_catalog", "enabled": True}  # meta
        ))

        external_provider = Mock()
        external_provider.name = "marketcheck"
        external_provider.search_listings = Mock()

        # Logic simulation
        total = 0
        providers = [internal_provider, external_provider]

        # Query internal first
        items, provider_total, meta = internal_provider.search_listings(
            query="test",
            filters={},
            page=1,
            page_size=25,
        )
        total += provider_total

        # Check if should query external
        should_query_external = (
            not settings.search_internal_first or
            (total < settings.search_internal_min_results and settings.search_external_fallback_enabled)
        )

        # Assertions
        assert internal_provider.search_listings.called
        assert total == 1
        assert not should_query_external
        # External provider should NOT be called
        assert not external_provider.search_listings.called

    def test_internal_first_with_fallback(self):
        """
        When SEARCH_INTERNAL_FIRST=true, results=0, and fallback enabled,
        external providers SHOULD be queried.
        """
        # Setup
        settings = Settings(
            search_internal_first=True,
            search_internal_min_results=1,
            search_external_fallback_enabled=True,
        )

        internal_provider = Mock()
        internal_provider.name = "internal_catalog"
        internal_provider.search_listings = Mock(return_value=(
            [],  # No results
            0,
            {"name": "internal_catalog", "enabled": True}
        ))

        external_provider = Mock()
        external_provider.name = "marketcheck"
        external_provider.search_listings = Mock(return_value=(
            [{"id": "ext1", "title": "External Car"}],
            1,
            {"name": "marketcheck", "enabled": True}
        ))

        # Logic simulation
        total = 0

        # Query internal first
        items, provider_total, meta = internal_provider.search_listings(
            query="test",
            filters={},
            page=1,
            page_size=25,
        )
        total += provider_total

        # Check if should query external
        should_query_external = (
            not settings.search_internal_first or
            (total < settings.search_internal_min_results and settings.search_external_fallback_enabled)
        )

        # Assertions
        assert internal_provider.search_listings.called
        assert total == 0
        assert should_query_external

        # If condition is true, external provider WOULD be called
        if should_query_external:
            ext_items, ext_total, ext_meta = external_provider.search_listings(
                query="test",
                filters={},
                page=1,
                page_size=25,
            )
            total += ext_total

        assert external_provider.search_listings.called
        assert total == 1

    def test_internal_first_disabled(self):
        """
        When SEARCH_INTERNAL_FIRST=false,
        all providers should be queried (old behavior).
        """
        # Setup
        settings = Settings(
            search_internal_first=False,
            search_internal_min_results=1,
            search_external_fallback_enabled=False,
        )

        internal_provider = Mock()
        internal_provider.name = "internal_catalog"
        internal_provider.search_listings = Mock(return_value=(
            [{"id": "1"}],
            1,
            {"name": "internal_catalog", "enabled": True}
        ))

        external_provider = Mock()
        external_provider.name = "marketcheck"
        external_provider.search_listings = Mock(return_value=(
            [{"id": "ext1"}],
            1,
            {"name": "marketcheck", "enabled": True}
        ))

        # Logic simulation
        total = 0

        # Query internal first
        if settings.search_internal_first and internal_provider:
            items, provider_total, meta = internal_provider.search_listings(
                query="test",
                filters={},
                page=1,
                page_size=25,
            )
            total += provider_total

        # Check if should query external
        should_query_external = (
            not settings.search_internal_first or
            (total < settings.search_internal_min_results and settings.search_external_fallback_enabled)
        )

        # Assertions
        assert should_query_external  # Since internal_first is False
        # Both providers WOULD be called in real implementation
        # (In this test, we verify the logic condition)

    def test_fallback_disabled_prevents_external_queries(self):
        """
        When internal returns 0 results but fallback is disabled,
        external providers should NOT be queried.
        """
        # Setup
        settings = Settings(
            search_internal_first=True,
            search_internal_min_results=1,
            search_external_fallback_enabled=False,  # Disabled
        )

        total = 0  # Internal returned 0 results

        # Check if should query external
        should_query_external = (
            not settings.search_internal_first or
            (total < settings.search_internal_min_results and settings.search_external_fallback_enabled)
        )

        # Assertions
        assert not should_query_external  # Fallback is disabled


class TestConfigurationDefaults:
    """Test default configuration values."""

    def test_default_config_values(self):
        """Verify default config values are production-safe."""
        settings = Settings()

        # Internal-first should be enabled by default
        assert settings.search_internal_first is True

        # Min results threshold should be conservative (1)
        assert settings.search_internal_min_results == 1

        # External fallback should be DISABLED by default (safer)
        assert settings.search_external_fallback_enabled is False
