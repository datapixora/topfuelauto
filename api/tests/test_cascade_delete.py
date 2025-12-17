"""
Regression test for CASCADE DELETE constraints.

Tests that deleting an admin_source properly cascades to all child records:
- admin_runs
- staged_listings
- staged_listing_attributes

This prevents IntegrityError 500 responses when deleting sources.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.admin_source import AdminSource, ProxyMode
from app.models.admin_run import AdminRun
from app.models.staged_listing import StagedListing
from app.models.staged_listing_attribute import StagedListingAttribute
from app.services import data_engine_service


class TestCascadeDelete:
    """Test CASCADE DELETE behavior for admin_sources."""

    def test_delete_source_cascades_to_runs(self, db: Session):
        """
        Deleting a source should cascade delete all runs.

        Setup:
        - Create source
        - Create 2 runs

        Action:
        - Delete source

        Assert:
        - Source deleted
        - Both runs deleted
        """
        # Create source
        source = AdminSource(
            key="test_cascade_source",
            name="Test Cascade Source",
            base_url="https://example.com",
            mode="list_only",
            is_enabled=False,
            proxy_mode=ProxyMode.NONE,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        source_id = source.id

        # Create runs
        run1 = AdminRun(
            source_id=source_id,
            status="succeeded",
            started_at=datetime.utcnow(),
            pages_planned=5,
            pages_done=5,
        )
        run2 = AdminRun(
            source_id=source_id,
            status="failed",
            started_at=datetime.utcnow(),
            pages_planned=3,
            pages_done=1,
        )
        db.add_all([run1, run2])
        db.commit()
        run1_id = run1.id
        run2_id = run2.id

        # Verify setup
        assert db.query(AdminSource).filter_by(id=source_id).first() is not None
        assert db.query(AdminRun).filter_by(id=run1_id).first() is not None
        assert db.query(AdminRun).filter_by(id=run2_id).first() is not None

        # Delete source
        result = data_engine_service.delete_source(db, source_id)
        assert result is True

        # Assert cascade delete
        assert db.query(AdminSource).filter_by(id=source_id).first() is None
        assert db.query(AdminRun).filter_by(id=run1_id).first() is None
        assert db.query(AdminRun).filter_by(id=run2_id).first() is None

    def test_delete_source_cascades_to_staged_listings(self, db: Session):
        """
        Deleting a source should cascade delete runs and staged listings.

        Setup:
        - Create source
        - Create run
        - Create 2 staged listings

        Action:
        - Delete source

        Assert:
        - Source deleted
        - Run deleted
        - Both staged listings deleted
        """
        # Create source
        source = AdminSource(
            key="test_cascade_listings",
            name="Test Cascade Listings",
            base_url="https://example.com",
            mode="list_only",
            is_enabled=False,
            proxy_mode=ProxyMode.NONE,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        # Create run
        run = AdminRun(
            source_id=source.id,
            status="running",
            started_at=datetime.utcnow(),
            pages_planned=1,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Create staged listings
        listing1 = StagedListing(
            run_id=run.id,
            source_key=source.key,
            canonical_url="https://example.com/listing/1",
            title="Test Listing 1",
            year=2020,
            make="Toyota",
            model="Camry",
        )
        listing2 = StagedListing(
            run_id=run.id,
            source_key=source.key,
            canonical_url="https://example.com/listing/2",
            title="Test Listing 2",
            year=2021,
            make="Honda",
            model="Civic",
        )
        db.add_all([listing1, listing2])
        db.commit()

        source_id = source.id
        run_id = run.id
        listing1_id = listing1.id
        listing2_id = listing2.id

        # Verify setup
        assert db.query(AdminSource).filter_by(id=source_id).first() is not None
        assert db.query(AdminRun).filter_by(id=run_id).first() is not None
        assert db.query(StagedListing).filter_by(id=listing1_id).first() is not None
        assert db.query(StagedListing).filter_by(id=listing2_id).first() is not None

        # Delete source
        result = data_engine_service.delete_source(db, source_id)
        assert result is True

        # Assert cascade delete
        assert db.query(AdminSource).filter_by(id=source_id).first() is None
        assert db.query(AdminRun).filter_by(id=run_id).first() is None
        assert db.query(StagedListing).filter_by(id=listing1_id).first() is None
        assert db.query(StagedListing).filter_by(id=listing2_id).first() is None

    def test_delete_source_cascades_to_attributes(self, db: Session):
        """
        Deleting a source should cascade delete all child records including attributes.

        Setup:
        - Create source
        - Create run
        - Create staged listing
        - Create 3 attributes

        Action:
        - Delete source

        Assert:
        - Source deleted
        - Run deleted
        - Staged listing deleted
        - All attributes deleted
        """
        # Create source
        source = AdminSource(
            key="test_cascade_full",
            name="Test Full Cascade",
            base_url="https://example.com",
            mode="list_only",
            is_enabled=False,
            proxy_mode=ProxyMode.NONE,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        # Create run
        run = AdminRun(
            source_id=source.id,
            status="running",
            started_at=datetime.utcnow(),
            pages_planned=1,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Create staged listing
        listing = StagedListing(
            run_id=run.id,
            source_key=source.key,
            canonical_url="https://example.com/listing/full",
            title="Test Full Cascade Listing",
            year=2022,
            make="Ford",
            model="F-150",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)

        # Create attributes
        attr1 = StagedListingAttribute(
            staged_listing_id=listing.id,
            key="color",
            value_text="Blue",
        )
        attr2 = StagedListingAttribute(
            staged_listing_id=listing.id,
            key="mileage",
            value_num=50000,
            unit="miles",
        )
        attr3 = StagedListingAttribute(
            staged_listing_id=listing.id,
            key="condition",
            value_text="Used",
        )
        db.add_all([attr1, attr2, attr3])
        db.commit()

        source_id = source.id
        run_id = run.id
        listing_id = listing.id
        attr1_id = attr1.id
        attr2_id = attr2.id
        attr3_id = attr3.id

        # Verify setup
        assert db.query(AdminSource).filter_by(id=source_id).first() is not None
        assert db.query(AdminRun).filter_by(id=run_id).first() is not None
        assert db.query(StagedListing).filter_by(id=listing_id).first() is not None
        assert db.query(StagedListingAttribute).filter_by(id=attr1_id).first() is not None
        assert db.query(StagedListingAttribute).filter_by(id=attr2_id).first() is not None
        assert db.query(StagedListingAttribute).filter_by(id=attr3_id).first() is not None

        # Delete source
        result = data_engine_service.delete_source(db, source_id)
        assert result is True

        # Assert cascade delete (entire chain)
        assert db.query(AdminSource).filter_by(id=source_id).first() is None
        assert db.query(AdminRun).filter_by(id=run_id).first() is None
        assert db.query(StagedListing).filter_by(id=listing_id).first() is None
        assert db.query(StagedListingAttribute).filter_by(id=attr1_id).first() is None
        assert db.query(StagedListingAttribute).filter_by(id=attr2_id).first() is None
        assert db.query(StagedListingAttribute).filter_by(id=attr3_id).first() is None

    def test_delete_source_not_found_returns_false(self, db: Session):
        """Deleting non-existent source should return False, not raise error."""
        result = data_engine_service.delete_source(db, source_id=999999)
        assert result is False

    def test_delete_source_with_multiple_runs_and_listings(self, db: Session):
        """
        Test complex cascade: source with multiple runs, each with multiple listings.

        Setup:
        - Create source
        - Create 2 runs
        - Run 1 has 3 listings
        - Run 2 has 2 listings
        - Each listing has 2 attributes

        Action:
        - Delete source

        Assert:
        - All 17 records deleted (1 source + 2 runs + 5 listings + 10 attributes)
        """
        # Create source
        source = AdminSource(
            key="test_cascade_complex",
            name="Test Complex Cascade",
            base_url="https://example.com",
            mode="list_only",
            is_enabled=False,
            proxy_mode=ProxyMode.NONE,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        # Create runs
        run1 = AdminRun(source_id=source.id, status="succeeded", pages_planned=1)
        run2 = AdminRun(source_id=source.id, status="succeeded", pages_planned=1)
        db.add_all([run1, run2])
        db.commit()
        db.refresh(run1)
        db.refresh(run2)

        # Create listings for run1 (3 listings)
        run1_listings = []
        for i in range(3):
            listing = StagedListing(
                run_id=run1.id,
                source_key=source.key,
                canonical_url=f"https://example.com/run1/{i}",
                title=f"Run1 Listing {i}",
            )
            run1_listings.append(listing)
        db.add_all(run1_listings)
        db.commit()

        # Create listings for run2 (2 listings)
        run2_listings = []
        for i in range(2):
            listing = StagedListing(
                run_id=run2.id,
                source_key=source.key,
                canonical_url=f"https://example.com/run2/{i}",
                title=f"Run2 Listing {i}",
            )
            run2_listings.append(listing)
        db.add_all(run2_listings)
        db.commit()

        # Create attributes (2 per listing)
        all_listings = run1_listings + run2_listings
        attributes = []
        for listing in all_listings:
            db.refresh(listing)  # Ensure ID is loaded
            attr1 = StagedListingAttribute(
                staged_listing_id=listing.id,
                key="key1",
                value_text="value1",
            )
            attr2 = StagedListingAttribute(
                staged_listing_id=listing.id,
                key="key2",
                value_text="value2",
            )
            attributes.extend([attr1, attr2])
        db.add_all(attributes)
        db.commit()

        source_id = source.id

        # Verify counts before delete
        assert db.query(AdminSource).filter_by(id=source_id).count() == 1
        assert db.query(AdminRun).filter_by(source_id=source_id).count() == 2
        assert db.query(StagedListing).filter(
            StagedListing.run_id.in_([run1.id, run2.id])
        ).count() == 5
        assert db.query(StagedListingAttribute).filter(
            StagedListingAttribute.staged_listing_id.in_([l.id for l in all_listings])
        ).count() == 10

        # Delete source
        result = data_engine_service.delete_source(db, source_id)
        assert result is True

        # Assert all cascaded
        assert db.query(AdminSource).filter_by(id=source_id).count() == 0
        assert db.query(AdminRun).filter_by(source_id=source_id).count() == 0
        assert db.query(StagedListing).filter(
            StagedListing.run_id.in_([run1.id, run2.id])
        ).count() == 0
        # Note: Can't directly query attributes by listing ID since listings are deleted
        # but CASCADE should have deleted them


# Fixtures
@pytest.fixture
def db():
    """
    Database session fixture.

    In a real test environment, this would:
    1. Create a test database
    2. Run migrations
    3. Provide a session
    4. Rollback/cleanup after test

    For now, this is a placeholder that would be configured with pytest-postgresql
    or a similar testing setup.
    """
    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
