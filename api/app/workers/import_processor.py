"""Celery task for processing CSV imports."""

import csv
import io
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.admin_import import AdminImport
from app.models.merged_listing import MergedListing
from app.models.merged_listing_attribute import MergedListingAttribute
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

BATCH_SIZE = 500  # Commit every 500 rows


def parse_price(value: str) -> Optional[Decimal]:
    """
    Parse price from various formats:
    - "$1 USD" -> 1.00
    - "6,700 USD" -> 6700.00
    - "92,745 USD" -> 92745.00
    """
    if not value or value.strip() in ('', 'N/A', 'NULL'):
        return None

    # Remove currency symbols and words
    cleaned = re.sub(r'[^\d,.]', '', value)
    # Remove commas
    cleaned = cleaned.replace(',', '')

    try:
        return Decimal(cleaned)
    except (ValueError, InvalidOperation):
        logger.warning(f"Failed to parse price: {value}")
        return None


def parse_mileage(value: str) -> Optional[int]:
    """
    Parse mileage from formats like:
    - "59,293 A" -> 59293
    - "1 N" -> None (not actual)
    - "0 E" -> None (exempt)
    """
    if not value or value.strip() in ('', 'N/A', 'NULL'):
        return None

    # Extract numeric part
    match = re.match(r'([\d,]+)', value)
    if match:
        numeric = match.group(1).replace(',', '')
        try:
            miles = int(numeric)
            # Exclude non-actual readings
            if 'N' in value or 'E' in value:
                return None
            return miles if miles > 0 else None
        except ValueError:
            return None

    return None


def parse_year(value: str) -> Optional[int]:
    """Parse year from string."""
    if not value or value.strip() in ('', 'N/A', 'NULL'):
        return None

    try:
        year = int(value.strip())
        # Sanity check (1900-2030)
        if 1900 <= year <= 2030:
            return year
    except ValueError:
        pass

    return None


def parse_sale_date(value: str) -> Optional[datetime]:
    """
    Parse sale date from format:
    - "12/17/2025 06:30 pm GMT+3:30"
    """
    if not value or value.strip() in ('', 'N/A', 'NULL'):
        return None

    try:
        # Extract date part before timezone
        date_part = value.split(' GMT')[0].strip()

        # Try multiple formats
        for fmt in [
            "%m/%d/%Y %I:%M %p",  # 12/17/2025 06:30 pm
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
        ]:
            try:
                return datetime.strptime(date_part, fmt)
            except ValueError:
                continue

    except Exception as e:
        logger.warning(f"Failed to parse date: {value} - {e}")

    return None


def build_listing_from_row(
    row: Dict[str, str],
    column_map: Dict[str, str],
    source_key: str
) -> tuple[Dict[str, Any], Dict[str, str]]:
    """
    Build MergedListing fields and extra attributes from CSV row using column mapping.

    Returns:
        (listing_fields, extra_attributes)
    """
    listing_fields = {}
    extra_attributes = {}

    # Reverse mapping: target_field -> csv_column
    reverse_map = {v: k for k, v in column_map.items()}

    # Required field: canonical_url
    if 'url' in reverse_map:
        listing_fields['canonical_url'] = row.get(reverse_map['url'], '').strip()
    else:
        raise ValueError("Missing required field 'url' in column mapping")

    # Optional fields with parsing
    if 'external_id' in reverse_map:
        listing_fields['source_listing_id'] = row.get(reverse_map['external_id'], '').strip() or None

    if 'year' in reverse_map:
        listing_fields['year'] = parse_year(row.get(reverse_map['year'], ''))

    if 'make' in reverse_map:
        listing_fields['make'] = row.get(reverse_map['make'], '').strip().upper() or None

    if 'model' in reverse_map:
        listing_fields['model'] = row.get(reverse_map['model'], '').strip() or None

    if 'price' in reverse_map:
        listing_fields['price_amount'] = parse_price(row.get(reverse_map['price'], ''))

    if 'mileage' in reverse_map:
        listing_fields['odometer_value'] = parse_mileage(row.get(reverse_map['mileage'], ''))

    if 'location' in reverse_map:
        listing_fields['location'] = row.get(reverse_map['location'], '').strip() or None

    if 'sale_date' in reverse_map:
        listing_fields['sale_datetime'] = parse_sale_date(row.get(reverse_map['sale_date'], ''))

    if 'title' in reverse_map:
        title_val = row.get(reverse_map['title'], '').strip()
        listing_fields['title'] = title_val[:500] if title_val else None  # Truncate to 500 chars

    # Set source_key
    listing_fields['source_key'] = source_key
    listing_fields['currency'] = 'USD'  # Default currency
    listing_fields['status'] = 'active'
    listing_fields['fetched_at'] = datetime.utcnow()

    # Store ALL unmapped columns as extra attributes
    for csv_col, csv_val in row.items():
        if csv_col not in column_map:
            # Store unmapped column as attribute
            extra_attributes[csv_col] = csv_val

    # Also store known fields that don't have dedicated columns
    known_extras = ['vin', 'damage', 'title_code', 'retail_value']
    for field in known_extras:
        if field in reverse_map:
            extra_attributes[field] = row.get(reverse_map[field], '').strip()

    return listing_fields, extra_attributes


@celery_app.task(bind=True)
def process_import(self, import_id: int):
    """
    Process a CSV import in the background.

    Args:
        import_id: AdminImport record ID
    """
    db: Session = SessionLocal()

    try:
        # Get import record
        admin_import = db.query(AdminImport).filter(AdminImport.id == import_id).first()
        if not admin_import:
            logger.error(f"Import {import_id} not found")
            return

        if not admin_import.file_data:
            logger.error(f"Import {import_id} has no file data")
            admin_import.status = "FAILED"
            admin_import.error_log = "No file data available"
            db.commit()
            return

        if not admin_import.column_map:
            logger.error(f"Import {import_id} has no column mapping")
            admin_import.status = "FAILED"
            admin_import.error_log = "No column mapping provided"
            db.commit()
            return

        # Mark as running
        admin_import.status = "RUNNING"
        admin_import.started_at = datetime.utcnow()
        admin_import.processed_rows = 0
        admin_import.created_count = 0
        admin_import.updated_count = 0
        admin_import.skipped_count = 0
        admin_import.error_count = 0
        db.commit()

        logger.info(f"Starting import {import_id}: {admin_import.filename}")

        # Parse CSV
        try:
            text = admin_import.file_data.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = admin_import.file_data.decode('latin-1')

        reader = csv.DictReader(io.StringIO(text))

        source_key = admin_import.source_key or "csv_import"
        column_map = admin_import.column_map

        errors = []
        batch = []
        row_num = 0

        for row in reader:
            row_num += 1

            try:
                # Build listing from row
                listing_fields, extra_attributes = build_listing_from_row(row, column_map, source_key)

                if not listing_fields.get('canonical_url'):
                    errors.append(f"Row {row_num}: Missing URL")
                    admin_import.error_count += 1
                    continue

                # Upsert MergedListing (idempotent by source_key + canonical_url)
                existing = db.query(MergedListing).filter(
                    MergedListing.source_key == source_key,
                    MergedListing.canonical_url == listing_fields['canonical_url']
                ).first()

                if existing:
                    # Update existing
                    for key, value in listing_fields.items():
                        if key not in ('id', 'created_at'):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()

                    # Update attributes
                    # Delete old attributes and recreate
                    db.query(MergedListingAttribute).filter(
                        MergedListingAttribute.listing_id == existing.id
                    ).delete()

                    for attr_key, attr_value in extra_attributes.items():
                        if attr_value and attr_value.strip():
                            attr = MergedListingAttribute(
                                listing_id=existing.id,
                                key=attr_key,
                                value_text=attr_value.strip()
                            )
                            db.add(attr)

                    admin_import.updated_count += 1

                else:
                    # Create new listing
                    new_listing = MergedListing(**listing_fields)
                    db.add(new_listing)
                    db.flush()  # Get ID

                    # Add attributes
                    for attr_key, attr_value in extra_attributes.items():
                        if attr_value and attr_value.strip():
                            attr = MergedListingAttribute(
                                listing_id=new_listing.id,
                                key=attr_key,
                                value_text=attr_value.strip()
                            )
                            db.add(attr)

                    admin_import.created_count += 1

                admin_import.processed_rows += 1

                # Batch commit
                if admin_import.processed_rows % BATCH_SIZE == 0:
                    db.commit()
                    logger.info(f"Import {import_id}: Processed {admin_import.processed_rows}/{admin_import.total_rows}")

            except Exception as e:
                error_msg = f"Row {row_num}: {type(e).__name__}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                admin_import.error_count += 1

                # Don't fail entire import on row errors
                if admin_import.error_count > 100:
                    # Too many errors, abort
                    logger.error(f"Import {import_id}: Too many errors (>{100}), aborting")
                    break

        # Final commit
        db.commit()

        # Mark as complete
        admin_import.status = "SUCCEEDED" if admin_import.error_count < admin_import.total_rows else "FAILED"
        admin_import.finished_at = datetime.utcnow()

        if errors:
            admin_import.error_log = "\n".join(errors[:100])  # Store first 100 errors

        db.commit()

        logger.info(
            f"Import {import_id} completed: "
            f"{admin_import.created_count} created, "
            f"{admin_import.updated_count} updated, "
            f"{admin_import.error_count} errors"
        )

    except Exception as e:
        logger.error(f"Import {import_id} failed: {type(e).__name__}: {e}", exc_info=True)

        try:
            admin_import.status = "FAILED"
            admin_import.finished_at = datetime.utcnow()
            admin_import.error_log = f"{type(e).__name__}: {e}"
            db.commit()
        except Exception:
            pass

    finally:
        db.close()
