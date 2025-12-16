"""Add proxy_mode, proxy_id, proxy_enabled to admin_sources

Revision ID: 0020_source_proxy_mode
Revises: 0019_proxy_endpoints
Create Date: 2025-12-16 20:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0020_source_proxy_mode"
down_revision = "0019_proxy_endpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing enum if it exists (from failed migration)
    op.execute("DROP TYPE IF EXISTS proxymode CASCADE")

    # Create enum type for proxy_mode with lowercase values
    op.execute("CREATE TYPE proxymode AS ENUM ('none', 'pool', 'manual')")

    # Add columns to admin_sources
    op.add_column("admin_sources", sa.Column("proxy_mode", sa.Enum('none', 'pool', 'manual', name='proxymode', create_type=False), nullable=False, server_default="none"))
    op.add_column("admin_sources", sa.Column("proxy_id", sa.Integer(), nullable=True))
    op.add_column("admin_sources", sa.Column("proxy_enabled", sa.Boolean(), nullable=False, server_default="false"))

    # Add foreign key constraint for proxy_id
    op.create_foreign_key("fk_admin_sources_proxy", "admin_sources", "proxies", ["proxy_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint("fk_admin_sources_proxy", "admin_sources", type_="foreignkey")

    # Drop columns
    op.drop_column("admin_sources", "proxy_enabled")
    op.drop_column("admin_sources", "proxy_id")
    op.drop_column("admin_sources", "proxy_mode")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS proxymode")
