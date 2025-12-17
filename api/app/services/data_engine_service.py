from datetime import datetime, timedelta
from typing import Any, List, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.admin_source import AdminSource
from app.models.admin_run import AdminRun
from app.models.staged_listing import StagedListing
from app.models.staged_listing_attribute import StagedListingAttribute
from app.models.merged_listing import MergedListing
from app.models.merged_listing_attribute import MergedListingAttribute
from app.models.proxy_endpoint import ProxyEndpoint
from app.schemas import data_engine as schemas
from app.services import crypto_service

logger = logging.getLogger(__name__)


# ============================================================================
# Proxy Encryption Helpers
# ============================================================================

PROXY_ENCRYPTED_FIELDS = ["proxy_password", "proxy_username"]


def get_proxy_pool_summary(db: Session) -> Optional[schemas.ProxyPoolSummary]:
    """
    Get summary of enabled proxies in the pool.
    Returns enabled count, weight sum, and last exit IP from most recent check.
    """
    enabled_proxies = db.query(ProxyEndpoint).filter(ProxyEndpoint.is_enabled.is_(True)).all()

    if not enabled_proxies:
        return None

    enabled_count = len(enabled_proxies)
    weight_sum = sum(p.weight for p in enabled_proxies)

    # Get the most recently checked proxy's exit IP
    last_checked = (
        db.query(ProxyEndpoint)
        .filter(ProxyEndpoint.is_enabled.is_(True), ProxyEndpoint.last_check_at.isnot(None))
        .order_by(ProxyEndpoint.last_check_at.desc())
        .first()
    )
    last_exit_ip = last_checked.last_exit_ip if last_checked else None

    return schemas.ProxyPoolSummary(
        enabled_count=enabled_count,
        weight_sum=weight_sum,
        last_exit_ip=last_exit_ip
    )


def encrypt_proxy_settings(settings_json: Optional[dict]) -> Optional[dict]:
    """
    Encrypt sensitive proxy fields in settings_json.
    Fields encrypted: proxy_password, proxy_username
    """
    if not settings_json:
        return settings_json

    result = settings_json.copy()
    for field in PROXY_ENCRYPTED_FIELDS:
        if field in result and result[field]:
            try:
                result[field] = crypto_service.encrypt_string(result[field])
            except Exception as e:
                logger.error(f"Failed to encrypt {field}: {e}")
                raise ValueError(f"Failed to encrypt proxy credentials")

    return result


def decrypt_proxy_settings(settings_json: Optional[dict]) -> Optional[dict]:
    """
    Decrypt sensitive proxy fields in settings_json for display/use.
    Returns a copy with decrypted fields.
    """
    if not settings_json:
        return settings_json

    result = settings_json.copy()
    for field in PROXY_ENCRYPTED_FIELDS:
        if field in result and result[field]:
            try:
                result[field] = crypto_service.decrypt_string(result[field])
            except Exception as e:
                logger.warning(f"Failed to decrypt {field}: {e}")
                # Keep encrypted value if decryption fails

    return result


# ============================================================================
# Auto-Merge Rules
# ============================================================================

DEFAULT_MERGE_RULES = {
    "auto_merge_enabled": False,
    "require_year_make_model": True,
    "require_price_or_url": True,
    "min_confidence_score": None,
}


def resolve_merge_rules(source: Any) -> dict:
    """Return merge rules with defaults, honoring legacy settings_json.auto_merge_enabled."""
    rules = DEFAULT_MERGE_RULES.copy()

    # Prefer explicit merge_rules column
    if getattr(source, "merge_rules", None):
        try:
            rules.update({k: v for k, v in (source.merge_rules or {}).items() if v is not None})
        except Exception:
            logger.warning("Failed to parse merge_rules for source %s", getattr(source, "key", "?"))

    # Backwards compatibility: settings_json.auto_merge_enabled
    settings = getattr(source, "settings_json", None) or {}
    if settings.get("auto_merge_enabled"):
        rules["auto_merge_enabled"] = True

    return rules


def normalize_merge_rules(incoming: Optional[dict], settings_json: Optional[dict]) -> dict:
    """
    Combine defaults with incoming merge_rules payload and legacy auto_merge_enabled flag.
    """
    rules = DEFAULT_MERGE_RULES.copy()
    if incoming:
        rules.update({k: v for k, v in incoming.items() if v is not None})
    elif settings_json and settings_json.get("auto_merge_enabled"):
        rules["auto_merge_enabled"] = True
    return rules


# ============================================================================
# Block tracking
# ============================================================================

def recent_block_count(db: Session, source_id: int, within_minutes: int = 30) -> int:
    window_start = datetime.utcnow() - timedelta(minutes=within_minutes)
    return (
        db.query(AdminRun)
        .filter(
            AdminRun.source_id == source_id,
            AdminRun.status == "blocked",
            AdminRun.created_at >= window_start,
        )
        .count()
    )


def record_block_event(
    db: Session,
    source: AdminSource,
    block_reason: str,
    diagnostics: dict,
    cooldown_hours: int = 6,
    threshold: int = 2,
) -> None:
    """Update source after a blocked run with optional cooldown."""
    now = datetime.utcnow()
    source.last_block_reason = block_reason
    source.last_blocked_at = now
    source.failure_count += 1

    # If repeated blocks within window, pause
    if recent_block_count(db, source.id, within_minutes=30) >= threshold - 1:
        source.cooldown_until = now + timedelta(hours=cooldown_hours)
        source.next_run_at = source.cooldown_until
        source.disabled_reason = f"Auto-paused after repeated blocks ({block_reason}) until {source.cooldown_until.isoformat()}Z"
    else:
        # shorter backoff
        source.next_run_at = now + timedelta(minutes=max(source.schedule_minutes * 2, 30))

    db.add(source)


def record_proxy_failure(
    db: Session,
    source: AdminSource,
    error: str,
    cooldown_minutes: int = 60,
    threshold: int = 2,
) -> None:
    """Pause source if proxy failures repeat."""
    now = datetime.utcnow()
    source.failure_count += 1
    source.last_block_reason = f"Proxy failure: {error}"
    recent_failures = (
        db.query(AdminRun)
        .filter(
            AdminRun.source_id == source.id,
            AdminRun.status == "proxy_failed",
            AdminRun.created_at >= now - timedelta(minutes=30),
        )
        .count()
    )
    if recent_failures >= threshold - 1:
        source.cooldown_until = now + timedelta(minutes=cooldown_minutes)
        source.next_run_at = source.cooldown_until
        source.disabled_reason = f"Auto-paused after proxy failures until {source.cooldown_until.isoformat()}Z"
    else:
        source.next_run_at = now + timedelta(minutes=max(source.schedule_minutes * 2, 30))
    db.add(source)


def should_auto_merge(db: Session, source: Any, staged_listing: Any) -> tuple[bool, Optional[str]]:
    """
    Decide if a staged listing meets auto-approval criteria.

    Returns: (should_auto_approve: bool, reason_if_rejected)
    """
    rules = resolve_merge_rules(source)

    if not rules.get("auto_merge_enabled"):
        return False, "Auto-merge disabled"

    # Required fields: year + make + model
    if rules.get("require_year_make_model", True):
        if not (staged_listing.year and staged_listing.make and staged_listing.model):
            return False, "Missing year/make/model"

    # Require price or canonical URL (url should always be present but guard empties)
    if rules.get("require_price_or_url", True):
        has_price = staged_listing.price_amount is not None
        has_url = bool(getattr(staged_listing, "canonical_url", None))
        if not (has_price or has_url):
            return False, "Missing price and URL"

    # Confidence threshold
    min_conf = rules.get("min_confidence_score")
    if min_conf is not None:
        score = staged_listing.confidence_score
        if score is None or float(score) < float(min_conf):
            return False, f"Confidence {score or 0} below {min_conf}"

    # Duplicate check
    from app.models.merged_listing import MergedListing

    existing = (
        db.query(MergedListing)
        .filter(MergedListing.canonical_url == staged_listing.canonical_url)
        .first()
    )
    if existing:
        return False, f"Duplicate merged #{existing.id}"

    # Basic quality sanity
    if staged_listing.price_amount is not None and staged_listing.price_amount <= 0:
        return False, "Invalid price"

    if staged_listing.year is not None and (staged_listing.year < 1900 or staged_listing.year > 2035):
        return False, f"Year out of range ({staged_listing.year})"

    return True, None


def auto_merge_listing(db: Session, staged_listing: Any) -> Any:
    """
    Auto-merge a staged listing to merged_listings.
    Returns the merged listing.
    """
    # Prepare listing data
    listing_data = {
        "title": staged_listing.title,
        "year": staged_listing.year,
        "make": staged_listing.make,
        "model": staged_listing.model,
        "price_amount": staged_listing.price_amount,
        "currency": staged_listing.currency,
        "confidence_score": staged_listing.confidence_score,
        "odometer_value": staged_listing.odometer_value,
        "location": staged_listing.location,
        "listed_at": staged_listing.listed_at,
        "sale_datetime": staged_listing.sale_datetime,
        "fetched_at": staged_listing.fetched_at,
        "status": staged_listing.status,
    }

    # Prepare attributes
    attributes = [
        {
            "key": attr.key,
            "value_text": attr.value_text,
            "value_num": attr.value_num,
            "value_bool": attr.value_bool,
            "unit": attr.unit,
        }
        for attr in staged_listing.attributes
    ]

    # Upsert to merged_listings
    merged = upsert_merged_listing(
        db,
        source_key=staged_listing.source_key,
        canonical_url=staged_listing.canonical_url,
        listing_data=listing_data,
        attributes=attributes,
    )

    # Delete staged listing after merge
    db.delete(staged_listing)

    return merged


# ============================================================================
# Admin Source CRUD
# ============================================================================

def create_source(db: Session, source: schemas.AdminSourceCreate) -> AdminSource:
    """Create a new admin source (encrypts proxy credentials in settings_json)."""
    source_data = source.dict(exclude_unset=True)

    # Encrypt proxy credentials if present in settings_json
    if source_data.get("settings_json"):
        source_data["settings_json"] = encrypt_proxy_settings(source_data["settings_json"])

    # Normalize merge rules (defaults + legacy auto_merge flag)
    source_data["merge_rules"] = normalize_merge_rules(
        source_data.pop("merge_rules", None),
        source_data.get("settings_json"),
    )

    db_source = AdminSource(**source_data)
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
    """Update an admin source (encrypts proxy credentials in settings_json)."""
    db_source = get_source(db, source_id)
    if not db_source:
        return None

    update_data = source_update.dict(exclude_unset=True)

    # Handle proxy_mode changes
    if "proxy_mode" in update_data:
        from app.models.data_source import ProxyMode
        proxy_mode = update_data["proxy_mode"]

        if proxy_mode == ProxyMode.POOL:
            # Clear manual proxy fields from settings_json when switching to pool
            if "settings_json" not in update_data:
                update_data["settings_json"] = db_source.settings_json.copy() if db_source.settings_json else {}
            if update_data["settings_json"]:
                update_data["settings_json"].pop("proxy_enabled", None)
                update_data["settings_json"].pop("proxy_url", None)
                update_data["settings_json"].pop("proxy_host", None)
                update_data["settings_json"].pop("proxy_port", None)
                update_data["settings_json"].pop("proxy_username", None)
                update_data["settings_json"].pop("proxy_password", None)
                update_data["settings_json"].pop("proxy_type", None)
            # Update proxy_enabled for compatibility
            update_data["proxy_enabled"] = True

        elif proxy_mode == ProxyMode.MANUAL:
            # Manual mode keeps settings_json proxy config
            # Update proxy_enabled for compatibility
            update_data["proxy_enabled"] = True

        elif proxy_mode == ProxyMode.NONE:
            # Disable proxy
            update_data["proxy_enabled"] = False
            if "proxy_id" not in update_data:
                update_data["proxy_id"] = None

    # Encrypt proxy credentials if settings_json is being updated
    if "settings_json" in update_data and update_data["settings_json"]:
        update_data["settings_json"] = encrypt_proxy_settings(update_data["settings_json"])

    # Merge rules normalization (respect legacy toggle if merge_rules omitted)
    if "merge_rules" in update_data or "settings_json" in update_data:
        incoming_rules = update_data.pop("merge_rules", None) if "merge_rules" in update_data else None
        # Use current settings_json if not being updated
        settings_json = update_data.get("settings_json", db_source.settings_json)
        update_data["merge_rules"] = normalize_merge_rules(incoming_rules, settings_json)

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
    try:
        db_source = get_source(db, source_id)
        if not db_source:
            logger.warning(f"delete_source: source_id={source_id} not found")
            return False

        logger.info(f"Deleting source {source_id} ({db_source.key})")
        db.delete(db_source)
        db.commit()
        logger.info(f"Successfully deleted source {source_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {type(e).__name__}: {e}")
        db.rollback()
        raise  # Re-raise to let the router handle HTTP response


def get_due_sources(db: Session) -> List[AdminSource]:
    """Get sources that are due to run (enabled and next_run_at <= now)."""
    now = datetime.utcnow()
    return (
        db.query(AdminSource)
        .filter(
            AdminSource.is_enabled.is_(True),
            or_(AdminSource.cooldown_until.is_(None), AdminSource.cooldown_until <= now),
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
        existing.auto_approved = False  # re-evaluate with new data each run
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
