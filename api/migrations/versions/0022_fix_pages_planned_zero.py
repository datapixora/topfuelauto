"""Fix pages_planned=0 to prevent division errors

Revision ID: 0022_fix_pages_planned_zero
Revises: 0021_fix_proxy_mode_case
Create Date: 2025-12-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0022_fix_pages_planned_zero"
down_revision = "0021_fix_proxy_mode_case"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix pages_planned=0 values to prevent division by zero errors in progress calculations.

    Changes:
    1. Update existing rows with pages_planned=0 to pages_planned=1
    2. Change column default from 0 to 1
    """
    # Step 1: Update existing data
    op.execute("""
        UPDATE admin_runs
        SET pages_planned = 1
        WHERE pages_planned = 0
    """)

    # Step 2: Update column default
    op.execute("ALTER TABLE admin_runs ALTER COLUMN pages_planned SET DEFAULT 1")


def downgrade() -> None:
    """
    Revert pages_planned default back to 0 (not recommended).

    Note: Does not revert data changes (keeps pages_planned=1 for safety).
    """
    op.execute("ALTER TABLE admin_runs ALTER COLUMN pages_planned SET DEFAULT 0")
