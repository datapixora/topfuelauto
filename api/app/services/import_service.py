"""Service for CSV import processing."""

import csv
import hashlib
import io
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.admin_import import AdminImport
from app.models.merged_listing import MergedListing
from app.models.merged_listing_attribute import MergedListingAttribute

logger = logging.getLogger(__name__)


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of file data."""
    return hashlib.sha256(data).hexdigest()


def detect_csv_structure(file_data: bytes, preview_rows: int = 20) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """
    Parse CSV and detect headers, preview rows, and total row count.

    Returns:
        (headers, preview_rows, total_rows)
    """
    # Decode with BOM handling
    try:
        text = file_data.decode('utf-8-sig')  # Handles UTF-8 BOM
    except UnicodeDecodeError:
        text = file_data.decode('latin-1')  # Fallback

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    preview = []
    total_count = 0

    for i, row in enumerate(reader):
        total_count += 1
        if i < preview_rows:
            preview.append(dict(row))

    return headers, preview, total_count


def suggest_column_mapping(headers: List[str]) -> Dict[str, str]:
    """
    Suggest default mapping from CSV columns to target fields.

    Target fields for MergedListing:
    - canonical_url (required)
    - title
    - year
    - make
    - model
    - price_amount
    - currency
    - odometer_value
    - location
    - sale_datetime
    - source_listing_id

    Returns dict: {csv_column: target_field}
    """
    mapping = {}

    # Mapping rules (case-insensitive matching)
    rules = {
        # URL (required)
        "url": ["url", "lot url", "link", "listing url", "listing_url"],

        # Basic fields
        "year": ["year"],
        "make": ["make", "manufacturer"],
        "model": ["model"],

        # Price
        "price": ["price", "current bid", "current_bid", "bid", "sale price", "sale_price"],

        # Identifiers
        "external_id": ["lot", "lot/inv #", "lot_inv", "lot #", "lot_number", "inv", "inventory"],

        # Odometer
        "mileage": ["odometer", "mileage", "miles", "km"],

        # Location
        "location": ["location", "sale name", "sale_name", "site", "yard"],

        # Date
        "sale_date": ["sale date", "sale_date", "auction date", "auction_date", "date"],

        # Title
        "title": ["title", "description", "name"],

        # VIN
        "vin": ["vin", "vin #", "vin_number"],

        # Retail value
        "retail_value": ["est. retail value", "est retail value", "retail value", "retail_value", "estimated value"],

        # Damage
        "damage": ["damage", "damage description", "damage_description"],

        # Title code
        "title_code": ["title code", "title_code", "title status", "title_status"],
    }

    # Match headers to target fields
    for csv_col in headers:
        lower_col = csv_col.lower().strip()

        for target_field, patterns in rules.items():
            if lower_col in patterns:
                mapping[csv_col] = target_field
                break

    return mapping


def create_import(
    db: Session,
    filename: str,
    file_data: bytes,
    content_type: str,
    source_key: Optional[str] = None
) -> AdminImport:
    """
    Create a new import record with preview and suggested mapping.
    """
    # Compute hash
    sha256 = compute_sha256(file_data)

    # Check for duplicate (same file already uploaded)
    existing = db.query(AdminImport).filter(AdminImport.sha256 == sha256).first()
    if existing:
        logger.info(f"Import with SHA256 {sha256} already exists (id={existing.id})")
        # Return existing import if it's not completed
        if existing.status not in ('SUCCEEDED', 'FAILED'):
            return existing

    # Parse CSV
    try:
        headers, preview, total_rows = detect_csv_structure(file_data)
    except Exception as e:
        logger.error(f"Failed to parse CSV: {e}")
        raise ValueError(f"Invalid CSV file: {e}")

    if not headers:
        raise ValueError("CSV file has no headers")

    if total_rows == 0:
        raise ValueError("CSV file has no data rows")

    # Suggest mapping
    suggested_mapping = suggest_column_mapping(headers)

    # Create import record
    admin_import = AdminImport(
        source_key=source_key,
        filename=filename,
        content_type=content_type,
        file_size=len(file_data),
        sha256=sha256,
        file_data=file_data,  # Store in DB (for modest files)
        status="UPLOADED",
        total_rows=total_rows,
        detected_headers=headers,
        column_map=suggested_mapping,  # Initial suggestion
        sample_preview=preview,
    )

    db.add(admin_import)
    db.commit()
    db.refresh(admin_import)

    logger.info(f"Created import {admin_import.id}: {filename} ({total_rows} rows)")

    return admin_import


def get_import(db: Session, import_id: int) -> Optional[AdminImport]:
    """Get import by ID."""
    return db.query(AdminImport).filter(AdminImport.id == import_id).first()


def list_imports(db: Session, limit: int = 50, offset: int = 0) -> List[AdminImport]:
    """List recent imports."""
    return (
        db.query(AdminImport)
        .order_by(desc(AdminImport.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )


def update_import_mapping(db: Session, import_id: int, column_map: Dict[str, str]) -> AdminImport:
    """Update column mapping for an import."""
    admin_import = get_import(db, import_id)
    if not admin_import:
        raise ValueError(f"Import {import_id} not found")

    admin_import.column_map = column_map
    admin_import.status = "READY"
    admin_import.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(admin_import)

    return admin_import


def validate_column_mapping(column_map: Dict[str, str]) -> None:
    """
    Validate that required fields are mapped.

    Raises ValueError if validation fails.
    """
    # Check that at least 'url' is mapped
    target_fields = set(column_map.values())

    if "url" not in target_fields:
        raise ValueError("Required field 'url' must be mapped (for canonical_url)")

    logger.info(f"Column mapping validated: {len(column_map)} columns mapped")
