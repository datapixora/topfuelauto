"""Fix ProxyMode enum case to uppercase

Revision ID: 0021_fix_proxy_mode_case
Revises: 0020_source_proxy_mode
Create Date: 2025-12-17
"""

from alembic import op

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
    """
    # Step 1: Add new uppercase enum values to existing enum type
    op.execute("ALTER TYPE proxymode ADD VALUE IF NOT EXISTS 'NONE'")
    op.execute("ALTER TYPE proxymode ADD VALUE IF NOT EXISTS 'POOL'")
    op.execute("ALTER TYPE proxymode ADD VALUE IF NOT EXISTS 'MANUAL'")

    # Step 2: Update existing lowercase values to uppercase
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

    # Step 3: Drop old lowercase enum values
    # Note: We cannot directly drop enum values in PostgreSQL, so we recreate the enum
    # First, convert the column to text temporarily
    op.execute("ALTER TABLE admin_sources ALTER COLUMN proxy_mode TYPE text")

    # Drop old enum type
    op.execute("DROP TYPE IF EXISTS proxymode")

    # Create new enum type with only uppercase values
    op.execute("CREATE TYPE proxymode AS ENUM ('NONE', 'POOL', 'MANUAL')")

    # Convert column back to enum type
    op.execute("""
        ALTER TABLE admin_sources
        ALTER COLUMN proxy_mode TYPE proxymode
        USING proxy_mode::proxymode
    """)

    # Set default value
    op.execute("ALTER TABLE admin_sources ALTER COLUMN proxy_mode SET DEFAULT 'NONE'::proxymode")


def downgrade() -> None:
    """Revert to lowercase enum values (not recommended for production)."""
    # Convert column to text
    op.execute("ALTER TABLE admin_sources ALTER COLUMN proxy_mode TYPE text")

    # Drop uppercase enum
    op.execute("DROP TYPE IF EXISTS proxymode")

    # Create lowercase enum
    op.execute("CREATE TYPE proxymode AS ENUM ('none', 'pool', 'manual')")

    # Update values to lowercase
    op.execute("""
        UPDATE admin_sources
        SET proxy_mode = LOWER(proxy_mode)
    """)

    # Convert column back to enum
    op.execute("""
        ALTER TABLE admin_sources
        ALTER COLUMN proxy_mode TYPE proxymode
        USING proxy_mode::proxymode
    """)

    # Set default
    op.execute("ALTER TABLE admin_sources ALTER COLUMN proxy_mode SET DEFAULT 'none'::proxymode")
