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

    This migration is idempotent - safe to run even if constraints already correct.
    """
    connection = op.get_bind()

    # Helper function to check if constraint exists
    def constraint_exists(table_name: str, constraint_name: str) -> bool:
        result = connection.execute(sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = :constraint_name
                AND conrelid = :table_name::regclass
            )
        """), {"constraint_name": constraint_name, "table_name": table_name})
        return result.scalar()

    # 1. Fix admin_runs.source_id -> admin_sources.id
    # Drop existing constraint (try both auto-generated and custom names)
    for constraint_name in ["admin_runs_source_id_fkey", "fk_admin_runs_source"]:
        if constraint_exists("admin_runs", constraint_name):
            op.drop_constraint(constraint_name, "admin_runs", type_="foreignkey")

    # Re-create with CASCADE
    op.create_foreign_key(
        "fk_admin_runs_source",
        "admin_runs",
        "admin_sources",
        ["source_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # 2. Fix staged_listings.run_id -> admin_runs.id
    # Drop existing constraint
    for constraint_name in ["staged_listings_run_id_fkey", "fk_staged_listings_run"]:
        if constraint_exists("staged_listings", constraint_name):
            op.drop_constraint(constraint_name, "staged_listings", type_="foreignkey")

    # Re-create with CASCADE
    op.create_foreign_key(
        "fk_staged_listings_run",
        "staged_listings",
        "admin_runs",
        ["run_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # 3. Fix staged_listing_attributes.staged_listing_id -> staged_listings.id
    # Drop existing constraint
    for constraint_name in ["staged_listing_attributes_staged_listing_id_fkey", "fk_staged_listing_attributes_listing"]:
        if constraint_exists("staged_listing_attributes", constraint_name):
            op.drop_constraint(constraint_name, "staged_listing_attributes", type_="foreignkey")

    # Re-create with CASCADE
    op.create_foreign_key(
        "fk_staged_listing_attributes_listing",
        "staged_listing_attributes",
        "staged_listings",
        ["staged_listing_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    """
    Revert to RESTRICT constraints (not recommended for production).

    Note: This removes CASCADE behavior, which could cause future delete failures.
    Only downgrade if absolutely necessary.
    """
    # 1. Revert admin_runs.source_id constraint
    op.drop_constraint("fk_admin_runs_source", "admin_runs", type_="foreignkey")
    op.create_foreign_key(
        "admin_runs_source_id_fkey",
        "admin_runs",
        "admin_sources",
        ["source_id"],
        ["id"],
        ondelete="RESTRICT"  # Default behavior
    )

    # 2. Revert staged_listings.run_id constraint
    op.drop_constraint("fk_staged_listings_run", "staged_listings", type_="foreignkey")
    op.create_foreign_key(
        "staged_listings_run_id_fkey",
        "staged_listings",
        "admin_runs",
        ["run_id"],
        ["id"],
        ondelete="RESTRICT"
    )

    # 3. Revert staged_listing_attributes.staged_listing_id constraint
    op.drop_constraint("fk_staged_listing_attributes_listing", "staged_listing_attributes", type_="foreignkey")
    op.create_foreign_key(
        "staged_listing_attributes_staged_listing_id_fkey",
        "staged_listing_attributes",
        "staged_listings",
        ["staged_listing_id"],
        ["id"],
        ondelete="RESTRICT"
    )
