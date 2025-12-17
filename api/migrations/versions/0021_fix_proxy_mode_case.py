"""Fix ProxyMode enum case to uppercase

Revision ID: 0021_fix_proxy_mode_case
Revises: 0020_source_proxy_mode
Create Date: 2025-12-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0021_fix_proxy_mode_case"
down_revision = "0020_source_proxy_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix ProxyMode enum to use uppercase values.

    This migration handles production databases that may have lowercase enum values
    created by the original 0020_source_proxy_mode migration.

    CRITICAL: PostgreSQL requires enum values to be committed before they can be used.
    We use autocommit_block to ensure new enum values are committed before data updates.
    """
    # Get the connection for autocommit operations
    connection = op.get_bind()

    # Step 1: Add new uppercase enum values using autocommit
    # This is required because PostgreSQL doesn't allow using new enum values
    # until the transaction that created them is committed
    with op.get_context().autocommit_block():
        connection.execute(sa.text("ALTER TYPE proxymode ADD VALUE IF NOT EXISTS 'NONE'"))
        connection.execute(sa.text("ALTER TYPE proxymode ADD VALUE IF NOT EXISTS 'POOL'"))
        connection.execute(sa.text("ALTER TYPE proxymode ADD VALUE IF NOT EXISTS 'MANUAL'"))

    # Step 2: Update existing lowercase values to uppercase
    # Now we can safely use the new enum values since they've been committed
    op.execute("""
        UPDATE admin_sources
        SET proxy_mode = 'NONE'::proxymode
        WHERE proxy_mode::text = 'none'
    """)
    op.execute("""
        UPDATE admin_sources
        SET proxy_mode = 'POOL'::proxymode
        WHERE proxy_mode::text = 'pool'
    """)
    op.execute("""
        UPDATE admin_sources
        SET proxy_mode = 'MANUAL'::proxymode
        WHERE proxy_mode::text = 'manual'
    """)

    # Step 3: Update default value to uppercase
    op.execute("ALTER TABLE admin_sources ALTER COLUMN proxy_mode SET DEFAULT 'NONE'::proxymode")


def downgrade() -> None:
    """
    Revert to lowercase enum values (not recommended for production).

    Note: This assumes lowercase enum values still exist in the enum type.
    In production, you should never downgrade this migration.
    """
    # Update data back to lowercase
    op.execute("""
        UPDATE admin_sources
        SET proxy_mode = 'none'::proxymode
        WHERE proxy_mode::text = 'NONE'
    """)
    op.execute("""
        UPDATE admin_sources
        SET proxy_mode = 'pool'::proxymode
        WHERE proxy_mode::text = 'POOL'
    """)
    op.execute("""
        UPDATE admin_sources
        SET proxy_mode = 'manual'::proxymode
        WHERE proxy_mode::text = 'MANUAL'
    """)

    # Revert default to lowercase
    op.execute("ALTER TABLE admin_sources ALTER COLUMN proxy_mode SET DEFAULT 'none'::proxymode")
