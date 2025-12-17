"""Fix CASCADE DELETE constraints for admin_sources deletion

Revision ID: 0023_fix_cascade_delete_constraints
Revises: 0022_fix_pages_planned_zero
Create Date: 2025-12-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0023_fix_cascade_delete_constraints"
down_revision = "0022_fix_pages_planned_zero"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ensure all FK constraints have proper ON DELETE CASCADE.

    Problem: DELETE /api/v1/admin/data/sources/{id} returns 500 IntegrityError
    Cause: FK constraints may not have CASCADE in production database

    Fix cascade chain:
    1. admin_sources ← admin_runs.source_id (CASCADE)
    2. admin_runs ← staged_listings.run_id (CASCADE)
    3. staged_listings ← staged_listing_attributes.staged_listing_id (CASCADE)

    This migration is idempotent - uses DROP CONSTRAINT IF EXISTS.
    """
    # 1) admin_runs.source_id -> admin_sources.id
    op.execute("ALTER TABLE admin_runs DROP CONSTRAINT IF EXISTS admin_runs_source_id_fkey")
    op.execute("ALTER TABLE admin_runs DROP CONSTRAINT IF EXISTS fk_admin_runs_source")
    op.create_foreign_key(
        "fk_admin_runs_source",
        "admin_runs",
        "admin_sources",
        ["source_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2) staged_listings.run_id -> admin_runs.id
    op.execute("ALTER TABLE staged_listings DROP CONSTRAINT IF EXISTS staged_listings_run_id_fkey")
    op.execute("ALTER TABLE staged_listings DROP CONSTRAINT IF EXISTS fk_staged_listings_run")
    op.create_foreign_key(
        "fk_staged_listings_run",
        "staged_listings",
        "admin_runs",
        ["run_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3) staged_listing_attributes.staged_listing_id -> staged_listings.id
    op.execute("ALTER TABLE staged_listing_attributes DROP CONSTRAINT IF EXISTS staged_listing_attributes_staged_listing_id_fkey")
    op.execute("ALTER TABLE staged_listing_attributes DROP CONSTRAINT IF EXISTS fk_staged_listing_attributes_listing")
    op.create_foreign_key(
        "fk_staged_listing_attributes_listing",
        "staged_listing_attributes",
        "staged_listings",
        ["staged_listing_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """
    Revert to constraints without CASCADE (not recommended for production).

    Note: This removes CASCADE behavior, which could cause future delete failures.
    Only downgrade if absolutely necessary.
    """
    # 3) Revert staged_listing_attributes constraint
    op.execute("ALTER TABLE staged_listing_attributes DROP CONSTRAINT IF EXISTS fk_staged_listing_attributes_listing")
    op.create_foreign_key(
        "staged_listing_attributes_staged_listing_id_fkey",
        "staged_listing_attributes",
        "staged_listings",
        ["staged_listing_id"],
        ["id"],
        ondelete=None,  # Default RESTRICT behavior
    )

    # 2) Revert staged_listings constraint
    op.execute("ALTER TABLE staged_listings DROP CONSTRAINT IF EXISTS fk_staged_listings_run")
    op.create_foreign_key(
        "staged_listings_run_id_fkey",
        "staged_listings",
        "admin_runs",
        ["run_id"],
        ["id"],
        ondelete=None,
    )

    # 1) Revert admin_runs constraint
    op.execute("ALTER TABLE admin_runs DROP CONSTRAINT IF EXISTS fk_admin_runs_source")
    op.create_foreign_key(
        "admin_runs_source_id_fkey",
        "admin_runs",
        "admin_sources",
        ["source_id"],
        ["id"],
        ondelete=None,
    )
