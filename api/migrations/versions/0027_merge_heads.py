"""Merge alembic heads

Revision ID: 0027_merge_heads
Revises: 0026_internal_catalog, 0025_public_plans_fields
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0027_merge_heads'
down_revision = ('0026_internal_catalog', '0025_public_plans_fields')
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migration - no schema changes needed."""
    pass


def downgrade() -> None:
    """Merge migration - no schema changes needed."""
    pass
