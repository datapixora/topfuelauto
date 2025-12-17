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
from app.models.search_field import SearchField
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
    source_key: str,
    db: Session
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Build MergedListing fields using search_fields registry.

    Returns:
        (listing_fields, extra_fields, raw_payload)
    """
    listing_fields = {}
    extra_fields = {}
    raw_payload = dict(row)  # Store original CSV row for backfill

    # Load search fields registry (cached per import)
    search_fields = db.query(SearchField).filter(SearchField.enabled == True).all()

    # Build mapping: CSV header -> SearchField
    csv_to_field = {}
    for field in search_fields:
        for alias in field.source_aliases:
            if alias in row:
                csv_to_field[alias] = field
                break

    # Reverse mapping from old column_map (for backwards compatibility)
    reverse_map = {v: k for k, v in column_map.items()}

    # Required field: canonical_url (special case, not in search_fields)
    if 'url' in reverse_map:
        listing_fields['canonical_url'] = row.get(reverse_map['url'], '').strip()
    else:
        raise ValueError("Missing required field 'url' in column mapping")

    # External ID (special case)
    if 'external_id' in reverse_map:
        listing_fields['source_listing_id'] = row.get(reverse_map['external_id'], '').strip() or None

    # Title (special case)
    if 'title' in reverse_map:
        title_val = row.get(reverse_map['title'], '').strip()
        listing_fields['title'] = title_val[:500] if title_val else None

    # Process fields from registry
    for csv_header, field in csv_to_field.items():
        value = row.get(csv_header, '').strip()
        if not value:
            continue

        # Parse value based on data_type
        parsed_value = None
        if field.data_type == 'integer':
            if field.key in ['year', 'mileage']:
                parsed_value = parse_year(value) if field.key == 'year' else parse_mileage(value)
            else:
                try:
                    parsed_value = int(value)
                except ValueError:
                    logger.warning(f"Failed to parse integer for {field.key}: {value}")
        elif field.data_type == 'decimal':
            if field.key == 'price':
                parsed_value = parse_price(value)
            else:
                try:
                    parsed_value = Decimal(value)
                except (ValueError, InvalidOperation):
                    logger.warning(f"Failed to parse decimal for {field.key}: {value}")
        elif field.data_type == 'date':
            if field.key == 'sale_date':
                parsed_value = parse_sale_date(value)
            else:
                try:
                    parsed_value = datetime.fromisoformat(value)
                except ValueError:
                    logger.warning(f"Failed to parse date for {field.key}: {value}")
        elif field.data_type == 'string':
            parsed_value = value if field.key not in ['make'] else value.upper()

        if parsed_value is None and field.data_type == 'string':
            parsed_value = value

        # Store in appropriate location
        if field.storage == 'core':
            # Map to core column names
            column_name_map = {
                'year': 'year',
                'make': 'make',
                'model': 'model',
                'price': 'price_amount',
                'mileage': 'odometer_value',
                'location': 'location',
                'sale_date': 'sale_datetime',
            }
            column_name = column_name_map.get(field.key, field.key)
            if column_name in ['year', 'make', 'model', 'price_amount', 'odometer_value', 'location', 'sale_datetime']:
                listing_fields[column_name] = parsed_value
        elif field.storage == 'extra':
            # Store in extra JSONB
            extra_fields[field.key] = parsed_value

    # Set defaults
    listing_fields['source_key'] = source_key
    listing_fields['currency'] = 'USD'
    listing_fields['status'] = 'active'
    listing_fields['fetched_at'] = datetime.utcnow()

    return listing_fields, extra_fields, raw_payload


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
                # Build listing from row using search_fields registry
                listing_fields, extra_fields, raw_payload = build_listing_from_row(row, column_map, source_key, db)

                if not listing_fields.get('canonical_url'):
                    errors.append(f"Row {row_num}: Missing URL")
                    admin_import.error_count += 1
                    continue

                # Add extra and raw_payload to listing fields
                listing_fields['extra'] = extra_fields
                listing_fields['raw_payload'] = raw_payload

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

                    admin_import.updated_count += 1

                else:
                    # Create new listing
                    new_listing = MergedListing(**listing_fields)
                    db.add(new_listing)
                    db.flush()  # Get ID

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


@celery_app.task(bind=True)
def backfill_extra_fields(self, import_id: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Backfill extra fields from raw_payload for listings.

    Can filter by:
    - import_id: Backfill listings from specific import
    - start_date/end_date: Backfill listings created in date range

    Args:
        import_id: Optional AdminImport ID
        start_date: Optional ISO date string (e.g., "2025-01-01")
        end_date: Optional ISO date string (e.g., "2025-12-31")
    """
    db: Session = SessionLocal()

    try:
        logger.info(f"Starting backfill: import_id={import_id}, date_range={start_date} to {end_date}")

        # Build query
        query = db.query(MergedListing).filter(MergedListing.raw_payload.isnot(None))

        if import_id:
            # Filter by import source_key (assuming import creates listings with consistent source_key)
            admin_import = db.query(AdminImport).filter(AdminImport.id == import_id).first()
            if admin_import:
                query = query.filter(MergedListing.source_key == (admin_import.source_key or "csv_import"))

        if start_date:
            query = query.filter(MergedListing.created_at >= datetime.fromisoformat(start_date))

        if end_date:
            query = query.filter(MergedListing.created_at <= datetime.fromisoformat(end_date))

        listings = query.all()
        logger.info(f"Found {len(listings)} listings to backfill")

        # Load enabled search fields
        search_fields = db.query(SearchField).filter(SearchField.enabled == True).all()

        # Build mapping: CSV header -> SearchField
        processed_count = 0
        updated_count = 0

        for listing in listings:
            if not listing.raw_payload:
                continue

            # Process raw_payload through search_fields registry
            extra_fields = {}
            raw_row = listing.raw_payload

            for field in search_fields:
                if field.storage != 'extra':
                    continue  # Skip core fields (already in core columns)

                # Find matching alias in raw_payload
                matched_value = None
                for alias in field.source_aliases:
                    if alias in raw_row:
                        matched_value = raw_row[alias]
                        break

                if not matched_value:
                    continue

                # Parse value based on data_type
                parsed_value = None
                if field.data_type == 'integer':
                    try:
                        parsed_value = int(matched_value)
                    except ValueError:
                        pass
                elif field.data_type == 'decimal':
                    try:
                        parsed_value = str(Decimal(matched_value))  # Store as string for JSONB
                    except (ValueError, InvalidOperation):
                        pass
                elif field.data_type == 'string':
                    parsed_value = matched_value

                if parsed_value is not None:
                    extra_fields[field.key] = parsed_value

            # Update listing.extra
            if extra_fields:
                # Merge with existing extra data
                current_extra = listing.extra or {}
                current_extra.update(extra_fields)
                listing.extra = current_extra
                listing.updated_at = datetime.utcnow()
                updated_count += 1

            processed_count += 1

            # Batch commit
            if processed_count % BATCH_SIZE == 0:
                db.commit()
                logger.info(f"Backfill progress: {processed_count}/{len(listings)} processed, {updated_count} updated")

        # Final commit
        db.commit()
        logger.info(f"Backfill complete: {processed_count} processed, {updated_count} updated")

        return {"processed": processed_count, "updated": updated_count}

    except Exception as e:
        logger.error(f"Backfill failed: {type(e).__name__}: {e}", exc_info=True)
        db.rollback()
        raise

    finally:
        db.close()
