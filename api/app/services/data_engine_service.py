from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.admin_source import AdminSource
from app.models.admin_run import AdminRun
from app.models.staged_listing import StagedListing
from app.models.staged_listing_attribute import StagedListingAttribute
from app.models.merged_listing import MergedListing
from app.models.merged_listing_attribute import MergedListingAttribute
from app.schemas import data_engine as schemas


# ============================================================================
# Admin Source CRUD
# ============================================================================

def create_source(db: Session, source: schemas.AdminSourceCreate) -> AdminSource:
    """Create a new admin source."""
    db_source = AdminSource(**source.dict())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source


def get_source(db: Session, source_id: int) -> Optional[AdminSource]:
    """Get an admin source by ID."""
    return db.query(AdminSource).filter(AdminSource.id == source_id).first()


def get_source_by_key(db: Session, key: str) -> Optional[AdminSource]:
    """Get an admin source by key."""
    return db.query(AdminSource).filter(AdminSource.key == key).first()


def list_sources(db: Session, skip: int = 0, limit: int = 100, enabled_only: bool = False) -> List[AdminSource]:
    """List all admin sources."""
    query = db.query(AdminSource)
    if enabled_only:
        query = query.filter(AdminSource.is_enabled.is_(True))
    return query.order_by(AdminSource.created_at.desc()).offset(skip).limit(limit).all()


def update_source(db: Session, source_id: int, source_update: schemas.AdminSourceUpdate) -> Optional[AdminSource]:
    """Update an admin source."""
    db_source = get_source(db, source_id)
    if not db_source:
        return None

    update_data = source_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_source, field, value)

    db_source.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_source)
    return db_source


def toggle_source(db: Session, source_id: int) -> Optional[AdminSource]:
    """Toggle source enabled/disabled status."""
    db_source = get_source(db, source_id)
    if not db_source:
        return None

    db_source.is_enabled = not db_source.is_enabled
    db_source.updated_at = datetime.utcnow()

    # Clear disabled_reason if re-enabling
    if db_source.is_enabled:
        db_source.disabled_reason = None
        db_source.failure_count = 0

    db.commit()
    db.refresh(db_source)
    return db_source


def delete_source(db: Session, source_id: int) -> bool:
    """Delete an admin source (and cascade delete runs/items)."""
    db_source = get_source(db, source_id)
    if not db_source:
        return False

    db.delete(db_source)
    db.commit()
    return True


def get_due_sources(db: Session) -> List[AdminSource]:
    """Get sources that are due to run (enabled and next_run_at <= now)."""
    now = datetime.utcnow()
    return (
        db.query(AdminSource)
        .filter(
            AdminSource.is_enabled.is_(True),
            or_(AdminSource.next_run_at.is_(None), AdminSource.next_run_at <= now),
        )
        .order_by(AdminSource.next_run_at.asc().nullsfirst())
        .all()
    )


# ============================================================================
# Admin Run CRUD
# ============================================================================

def create_run(db: Session, run: schemas.AdminRunCreate) -> AdminRun:
    """Create a new admin run."""
    db_run = AdminRun(**run.dict())
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


def get_run(db: Session, run_id: int) -> Optional[AdminRun]:
    """Get an admin run by ID."""
    return db.query(AdminRun).filter(AdminRun.id == run_id).first()


def list_runs(
    db: Session, source_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[AdminRun]:
    """List admin runs, optionally filtered by source."""
    query = db.query(AdminRun)
    if source_id:
        query = query.filter(AdminRun.source_id == source_id)
    return query.order_by(AdminRun.created_at.desc()).offset(skip).limit(limit).all()


def update_run(db: Session, run_id: int, run_update: schemas.AdminRunUpdate) -> Optional[AdminRun]:
    """Update an admin run."""
    db_run = get_run(db, run_id)
    if not db_run:
        return None

    update_data = run_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_run, field, value)

    db.commit()
    db.refresh(db_run)
    return db_run


# ============================================================================
# Staged Listing CRUD
# ============================================================================

def create_staged_listing(
    db: Session, listing: schemas.StagedListingCreate, attributes: Optional[List[schemas.StagedListingAttributeBase]] = None
) -> StagedListing:
    """Create a staged listing with optional attributes."""
    db_listing = StagedListing(**listing.dict())
    db.add(db_listing)
    db.flush()  # Get ID without committing

    if attributes:
        for attr in attributes:
            db_attr = StagedListingAttribute(staged_listing_id=db_listing.id, **attr.dict())
            db.add(db_attr)

    db.commit()
    db.refresh(db_listing)
    return db_listing


def upsert_staged_listing(
    db: Session,
    run_id: int,
    source_key: str,
    canonical_url: str,
    listing_data: dict,
    attributes: Optional[List[dict]] = None,
) -> StagedListing:
    """Upsert a staged listing by source_key + canonical_url."""
    existing = (
        db.query(StagedListing)
        .filter(
            and_(
                StagedListing.source_key == source_key,
                StagedListing.canonical_url == canonical_url,
            )
        )
        .first()
    )

    if existing:
        # Update existing
        for field, value in listing_data.items():
            if hasattr(existing, field):
                setattr(existing, field, value)
        existing.updated_at = datetime.utcnow()
        existing.run_id = run_id  # Update to latest run
        db_listing = existing
    else:
        # Create new
        db_listing = StagedListing(run_id=run_id, source_key=source_key, canonical_url=canonical_url, **listing_data)
        db.add(db_listing)

    db.flush()

    # Handle attributes (delete old, insert new)
    if attributes is not None:
        db.query(StagedListingAttribute).filter(StagedListingAttribute.staged_listing_id == db_listing.id).delete()
        for attr in attributes:
            db_attr = StagedListingAttribute(staged_listing_id=db_listing.id, **attr)
            db.add(db_attr)

    db.commit()
    db.refresh(db_listing)
    return db_listing


def get_staged_listing(db: Session, listing_id: int) -> Optional[StagedListing]:
    """Get a staged listing by ID."""
    return db.query(StagedListing).filter(StagedListing.id == listing_id).first()


def list_staged_listings(
    db: Session, run_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[StagedListing]:
    """List staged listings, optionally filtered by run."""
    query = db.query(StagedListing)
    if run_id:
        query = query.filter(StagedListing.run_id == run_id)
    return query.order_by(StagedListing.created_at.desc()).offset(skip).limit(limit).all()


# ============================================================================
# Merged Listing CRUD
# ============================================================================

def create_merged_listing(
    db: Session, listing: schemas.MergedListingCreate, attributes: Optional[List[schemas.MergedListingAttributeBase]] = None
) -> MergedListing:
    """Create a merged listing with optional attributes."""
    db_listing = MergedListing(**listing.dict())
    db.add(db_listing)
    db.flush()

    if attributes:
        for attr in attributes:
            db_attr = MergedListingAttribute(listing_id=db_listing.id, **attr.dict())
            db.add(db_attr)

    db.commit()
    db.refresh(db_listing)
    return db_listing


def upsert_merged_listing(
    db: Session,
    source_key: str,
    canonical_url: str,
    listing_data: dict,
    attributes: Optional[List[dict]] = None,
) -> MergedListing:
    """Upsert a merged listing by source_key + canonical_url."""
    existing = (
        db.query(MergedListing)
        .filter(
            and_(
                MergedListing.source_key == source_key,
                MergedListing.canonical_url == canonical_url,
            )
        )
        .first()
    )

    if existing:
        # Update existing
        for field, value in listing_data.items():
            if hasattr(existing, field):
                setattr(existing, field, value)
        existing.updated_at = datetime.utcnow()
        existing.merged_at = datetime.utcnow()  # Update merge timestamp
        db_listing = existing
    else:
        # Create new
        db_listing = MergedListing(source_key=source_key, canonical_url=canonical_url, **listing_data)
        db.add(db_listing)

    db.flush()

    # Handle attributes (delete old, insert new)
    if attributes is not None:
        db.query(MergedListingAttribute).filter(MergedListingAttribute.listing_id == db_listing.id).delete()
        for attr in attributes:
            db_attr = MergedListingAttribute(listing_id=db_listing.id, **attr)
            db.add(db_attr)

    db.commit()
    db.refresh(db_listing)
    return db_listing


def get_merged_listing(db: Session, listing_id: int) -> Optional[MergedListing]:
    """Get a merged listing by ID."""
    return db.query(MergedListing).filter(MergedListing.id == listing_id).first()


def list_merged_listings(db: Session, skip: int = 0, limit: int = 100) -> List[MergedListing]:
    """List merged listings."""
    return db.query(MergedListing).order_by(MergedListing.merged_at.desc()).offset(skip).limit(limit).all()
