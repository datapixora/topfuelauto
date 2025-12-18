"""Service for ingesting sold results into auction_sales table."""

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from typing import List, Dict, Any
from datetime import datetime
import logging

from app.models.auction_sale import AuctionSale

logger = logging.getLogger(__name__)


class SoldResultsIngestService:
    """
    Service for ingesting sold results into auction_sales table.

    Handles UPSERT logic with PostgreSQL ON CONFLICT clause to prevent duplicates
    while updating existing records with fresh data.
    """

    def ingest_sold_results(self, db: Session, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Upsert sold results into auction_sales table.

        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE to:
        - Insert new records
        - Update existing records (matched by vin + auction_source + lot_id)
        - Skip records with missing critical fields

        Args:
            db: SQLAlchemy database session
            results: List of sold result dictionaries from provider

        Returns:
            Dictionary with counts:
            - inserted: int (new records created)
            - updated: int (existing records updated)
            - skipped: int (records with missing data)
            - total: int (len of input results)
        """
        inserted = 0
        updated = 0
        skipped = 0

        for result in results:
            # Validate: Need at least VIN or lot_id
            if not result.get("vin") and not result.get("lot_id"):
                logger.warning(f"Skipping result without VIN or lot_id: {result.get('source_url', 'unknown')}")
                skipped += 1
                continue

            # Prepare data for database
            data = self._prepare_sale_data(result)

            try:
                # PostgreSQL UPSERT using SQLAlchemy
                stmt = insert(AuctionSale).values(data)

                # ON CONFLICT: Update if vin + auction_source + lot_id matches
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_auction_sale_vin_source_lot',
                    set_={
                        'sold_price': stmt.excluded.sold_price,
                        'sale_status': stmt.excluded.sale_status,
                        'sold_at': stmt.excluded.sold_at,
                        'location': stmt.excluded.location,
                        'odometer_miles': stmt.excluded.odometer_miles,
                        'damage': stmt.excluded.damage,
                        'condition': stmt.excluded.condition,
                        'attributes': stmt.excluded.attributes,
                        'raw_payload': stmt.excluded.raw_payload,
                        'source_url': stmt.excluded.source_url,
                        'updated_at': datetime.utcnow(),
                    }
                )

                # Execute UPSERT
                db.execute(stmt)

                # Check if it was an insert or update
                # Query to see if record existed before (rough heuristic using timestamps)
                existing = db.query(AuctionSale).filter(
                    AuctionSale.vin == data.get('vin'),
                    AuctionSale.auction_source == data['auction_source'],
                    AuctionSale.lot_id == data.get('lot_id')
                ).first()

                if existing:
                    # If created_at is very recent (within last second), likely inserted
                    time_since_creation = (datetime.utcnow() - existing.created_at).total_seconds()
                    if time_since_creation < 2:
                        inserted += 1
                    else:
                        updated += 1
                else:
                    # Fallback: couldn't determine, count as inserted
                    inserted += 1

            except Exception as e:
                logger.error(f"Failed to upsert sale: {e}", exc_info=True)
                skipped += 1
                continue

        # Commit all changes
        db.commit()

        logger.info(f"Ingest complete: {inserted} inserted, {updated} updated, {skipped} skipped")

        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "total": len(results)
        }

    def _prepare_sale_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare sale data for database insertion.

        Normalizes fields and ensures correct data types.

        Args:
            result: Raw result dictionary from provider

        Returns:
            Dictionary matching AuctionSale model fields
        """
        # Normalize VIN to uppercase if present
        vin = result.get("vin")
        if vin:
            vin = vin.upper().strip()

        return {
            "vin": vin,
            "lot_id": result.get("lot_id"),
            "auction_source": result.get("auction_source", "unknown"),
            "sale_status": result.get("sale_status", "unknown"),
            "sold_price": result.get("sold_price"),
            "currency": result.get("currency", "USD"),
            "sold_at": result.get("sold_at"),
            "location": result.get("location"),
            "odometer_miles": result.get("odometer_miles"),
            "damage": result.get("damage"),
            "condition": result.get("condition"),
            "attributes": result.get("attributes", {}),
            "raw_payload": result.get("raw_payload"),
            "source_url": result.get("source_url", ""),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
