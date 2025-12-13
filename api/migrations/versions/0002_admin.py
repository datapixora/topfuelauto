"""add is_admin and search events

Revision ID: 0002_admin
Revises: 0001_init
Create Date: 2025-12-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_admin'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_table(
        'search_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(length=255), nullable=False),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_events_query', 'search_events', ['query'], unique=False)
    op.create_index('ix_search_events_created_at', 'search_events', ['created_at'], unique=False)


def downgrade():
    op.drop_index('ix_search_events_created_at', table_name='search_events')
    op.drop_index('ix_search_events_query', table_name='search_events')
    op.drop_table('search_events')
    op.drop_column('users', 'is_admin')