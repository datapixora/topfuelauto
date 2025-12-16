"""Data Engine block cooldown and diagnostics

Revision ID: 0018_data_engine_block_cooldown
Revises: 0017_data_engine_merge_rules
Create Date: 2025-12-16 17:44:34
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0018_data_engine_block_cooldown"
down_revision = "0017_data_engine_merge_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('admin_sources', sa.Column('last_block_reason', sa.Text(), nullable=True))
    op.add_column('admin_sources', sa.Column('last_blocked_at', sa.DateTime(), nullable=True))
    op.add_column('admin_sources', sa.Column('cooldown_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('admin_sources', 'cooldown_until')
    op.drop_column('admin_sources', 'last_blocked_at')
    op.drop_column('admin_sources', 'last_block_reason')
