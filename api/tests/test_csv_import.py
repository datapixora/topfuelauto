"""Tests for CSV import system."""

import io
import pytest
from sqlalchemy.orm import Session

from app.models.admin_import import AdminImport
from app.models.merged_listing import MergedListing
from app.services.import_service import (
    compute_sha256,
    detect_csv_structure,
    suggest_column_mapping,
    create_import,
    validate_column_mapping,
)
from app.workers.import_processor import (
    parse_price,
    parse_mileage,
    parse_year,
    build_listing_from_row,
)


class TestImportService:
    """Test import service functions."""

    def test_compute_sha256(self):
        """Test SHA256 computation."""
        data = b"test data"
        hash1 = compute_sha256(data)
        hash2 = compute_sha256(data)

        assert hash1 == hash2  # Consistent
        assert len(hash1) == 64  # SHA256 is 64 hex chars
        assert isinstance(hash1, str)

    def test_detect_csv_structure(self):
        """Test CSV parsing and header detection."""
        csv_data = """Lot URL,Year,Make,Model,Price
https://example.com/lot1,2020,Ford,F-150,"5,000 USD"
https://example.com/lot2,2019,Toyota,Camry,"3,500 USD"
""".encode('utf-8')

        headers, preview, total = detect_csv_structure(csv_data, preview_rows=5)

        assert headers == ["Lot URL", "Year", "Make", "Model", "Price"]
        assert len(preview) == 2
        assert total == 2
        assert preview[0]["Year"] == "2020"
        assert preview[0]["Make"] == "Ford"

    def test_suggest_column_mapping(self):
        """Test column mapping heuristics."""
        headers = [
            "Lot URL",
            "Lot/Inv #",
            "Year",
            "Make",
            "Model",
            "Current bid",
            "Odometer",
            "Sale name",
        ]

        mapping = suggest_column_mapping(headers)

        assert mapping["Lot URL"] == "url"
        assert mapping["Lot/Inv #"] == "external_id"
        assert mapping["Year"] == "year"
        assert mapping["Make"] == "make"
        assert mapping["Model"] == "model"
        assert mapping["Current bid"] == "price"
        assert mapping["Odometer"] == "mileage"
        assert mapping["Sale name"] == "location"

    def test_validate_column_mapping_success(self):
        """Test mapping validation with required fields."""
        mapping = {"Lot URL": "url", "Year": "year", "Make": "make"}

        # Should not raise
        validate_column_mapping(mapping)

    def test_validate_column_mapping_missing_url(self):
        """Test mapping validation fails without URL."""
        mapping = {"Year": "year", "Make": "make"}

        with pytest.raises(ValueError, match="url.*must be mapped"):
            validate_column_mapping(mapping)


class TestImportProcessor:
    """Test import processing functions."""

    def test_parse_price(self):
        """Test price parsing from various formats."""
        assert parse_price("$1 USD") == 1.0
        assert parse_price("6,700 USD") == 6700.0
        assert parse_price("92,745 USD") == 92745.0
        assert parse_price("$15,000") == 15000.0
        assert parse_price("N/A") is None
        assert parse_price("") is None
        assert parse_price("invalid") is None

    def test_parse_mileage(self):
        """Test mileage parsing."""
        assert parse_mileage("59,293 A") == 59293
        assert parse_mileage("100,000 A") == 100000
        assert parse_mileage("1 N") is None  # Not actual
        assert parse_mileage("0 E") is None  # Exempt
        assert parse_mileage("N/A") is None
        assert parse_mileage("") is None

    def test_parse_year(self):
        """Test year parsing."""
        assert parse_year("2020") == 2020
        assert parse_year("2025") == 2025
        assert parse_year("1950") == 1950
        assert parse_year("invalid") is None
        assert parse_year("") is None
        assert parse_year("1899") is None  # Too old
        assert parse_year("2031") is None  # Too far in future

    def test_build_listing_from_row(self):
        """Test building listing from CSV row."""
        row = {
            "Lot URL": "https://example.com/lot123",
            "Lot/Inv #": "LOT123",
            "Year": "2020",
            "Make": "FORD",
            "Model": "F-150",
            "Current bid": "5,000 USD",
            "Odometer": "50,000 A",
            "Sale name": "NY - Albany",
        }

        column_map = {
            "Lot URL": "url",
            "Lot/Inv #": "external_id",
            "Year": "year",
            "Make": "make",
            "Model": "model",
            "Current bid": "price",
            "Odometer": "mileage",
            "Sale name": "location",
        }

        listing_fields, extra_attrs = build_listing_from_row(row, column_map, "test_import")

        assert listing_fields["canonical_url"] == "https://example.com/lot123"
        assert listing_fields["source_listing_id"] == "LOT123"
        assert listing_fields["year"] == 2020
        assert listing_fields["make"] == "FORD"
        assert listing_fields["model"] == "F-150"
        assert listing_fields["price_amount"] == 5000.0
        assert listing_fields["odometer_value"] == 50000
        assert listing_fields["location"] == "NY - Albany"
        assert listing_fields["source_key"] == "test_import"
        assert listing_fields["currency"] == "USD"
        assert listing_fields["status"] == "active"


class TestImportEndToEnd:
    """Integration tests for import workflow."""

    def test_create_import(self, db_session: Session):
        """Test creating an import record with preview."""
        csv_data = """URL,Year,Make,Model
https://example.com/lot1,2020,Ford,F-150
https://example.com/lot2,2019,Toyota,Camry
""".encode('utf-8')

        admin_import = create_import(
            db=db_session,
            filename="test.csv",
            file_data=csv_data,
            content_type="text/csv",
            source_key="test_source",
        )

        assert admin_import.id is not None
        assert admin_import.filename == "test.csv"
        assert admin_import.source_key == "test_source"
        assert admin_import.total_rows == 2
        assert admin_import.status == "UPLOADED"
        assert len(admin_import.detected_headers) == 4
        assert "URL" in admin_import.detected_headers
        assert len(admin_import.sample_preview) == 2
        assert admin_import.column_map["URL"] == "url"
        assert admin_import.column_map["Year"] == "year"

    def test_import_idempotency(self, db_session: Session):
        """Test that re-uploading same file returns existing import."""
        csv_data = """URL,Year,Make
https://example.com/lot1,2020,Ford
""".encode('utf-8')

        import1 = create_import(
            db=db_session,
            filename="test.csv",
            file_data=csv_data,
            content_type="text/csv",
        )

        import2 = create_import(
            db=db_session,
            filename="test2.csv",  # Different name, same content
            file_data=csv_data,
            content_type="text/csv",
        )

        # Should return same import (same SHA256)
        assert import1.id == import2.id
        assert import1.sha256 == import2.sha256


# Fixtures
@pytest.fixture
def db_session():
    """Mock database session for testing."""
    # Note: In a real test suite, this would create a test database
    # For now, this is a placeholder for the test structure
    from unittest.mock import Mock
    return Mock(spec=Session)
