"""Add search performance indexes to merged_listings

Revision ID: 0025_merged_search_idx
Revises: 0024_admin_imports
Create Date: 2025-12-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0025_merged_search_idx"
down_revision = "0024_admin_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add performance indexes for search queries on merged_listings.
    """
    # Price index (for price range queries)
    op.create_index(
        "ix_merged_listings_price",
        "merged_listings",
        ["price_amount"],
        postgresql_where=sa.text("price_amount IS NOT NULL"),
    )

    # Status index (for filtering active listings)
    op.create_index(
        "ix_merged_listings_status",
        "merged_listings",
        ["status"],
    )

    # Created timestamp index (for sorting by newest)
    op.create_index(
        "ix_merged_listings_created_at",
        "merged_listings",
        ["created_at"],
    )

    # Location index (for location filtering)
    op.create_index(
        "ix_merged_listings_location",
        "merged_listings",
        ["location"],
        postgresql_where=sa.text("location IS NOT NULL"),
    )

    # Sale datetime index (for auction date filtering)
    op.create_index(
        "ix_merged_listings_sale_datetime",
        "merged_listings",
        ["sale_datetime"],
        postgresql_where=sa.text("sale_datetime IS NOT NULL"),
    )

    # Composite index for common search pattern: make + model + year
    op.create_index(
        "ix_merged_listings_make_model_year",
        "merged_listings",
        ["make", "model", "year"],
    )

    # Composite index for status + created_at (common query: active listings sorted by newest)
    op.create_index(
        "ix_merged_listings_status_created",
        "merged_listings",
        ["status", "created_at"],
    )


def downgrade() -> None:
    """Drop search indexes."""
    op.drop_index("ix_merged_listings_status_created", "merged_listings")
    op.drop_index("ix_merged_listings_make_model_year", "merged_listings")
    op.drop_index("ix_merged_listings_sale_datetime", "merged_listings")
    op.drop_index("ix_merged_listings_location", "merged_listings")
    op.drop_index("ix_merged_listings_created_at", "merged_listings")
    op.drop_index("ix_merged_listings_status", "merged_listings")
    op.drop_index("ix_merged_listings_price", "merged_listings")
