"""Add auto-merge rules and confidence columns

Revision ID: 0017_data_engine_merge_rules
Revises: 0016_data_engine_schema
Create Date: 2025-12-16 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0017_data_engine_merge_rules"
down_revision = "0016_data_engine_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('admin_sources', sa.Column('merge_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column('staged_listings', sa.Column('auto_approved', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('staged_listings', sa.Column('confidence_score', sa.Numeric(precision=5, scale=3), nullable=True))

    op.add_column('merged_listings', sa.Column('confidence_score', sa.Numeric(precision=5, scale=3), nullable=True))


def downgrade() -> None:
    op.drop_column('merged_listings', 'confidence_score')
    op.drop_column('staged_listings', 'confidence_score')
    op.drop_column('staged_listings', 'auto_approved')
    op.drop_column('admin_sources', 'merge_rules')
