"""Seed internal_catalog provider

Revision ID: 0026_internal_catalog
Revises: 0025_merged_search_idx
Create Date: 2025-12-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0026_internal_catalog"
down_revision = "0025_merged_search_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add internal_catalog provider to provider_settings table.
    """
    # Use INSERT ... ON CONFLICT DO NOTHING for idempotency
    op.execute("""
        INSERT INTO provider_settings (key, enabled, priority, mode, settings_json, created_at, updated_at)
        VALUES ('internal_catalog', true, 10, 'search', '{}', NOW(), NOW())
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    """Remove internal_catalog provider."""
    op.execute("DELETE FROM provider_settings WHERE key = 'internal_catalog'")
