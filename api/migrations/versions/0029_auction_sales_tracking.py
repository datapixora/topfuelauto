"""Add auction_sales and auction_tracking tables

Revision ID: 0029_auction_sales_tracking
Revises: 0028_search_field_registry
Create Date: 2025-12-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0029_auction_sales_tracking'
down_revision = '0028_search_field_registry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create auction_sales table
    op.create_table(
        'auction_sales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vin', sa.String(length=17), nullable=True),
        sa.Column('lot_id', sa.String(length=100), nullable=True),
        sa.Column('auction_source', sa.String(length=50), nullable=False),
        sa.Column('sale_status', sa.String(length=50), nullable=False),
        sa.Column('sold_price', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('sold_at', sa.DateTime(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('odometer_miles', sa.Integer(), nullable=True),
        sa.Column('damage', sa.String(length=255), nullable=True),
        sa.Column('condition', sa.String(length=100), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vin', 'auction_source', 'lot_id', name='uq_auction_sale_vin_source_lot')
    )

    # Create indexes for auction_sales
    op.create_index('ix_auction_sales_id', 'auction_sales', ['id'])
    op.create_index('ix_auction_sales_vin', 'auction_sales', ['vin'])
    op.create_index('ix_auction_sales_lot_id', 'auction_sales', ['lot_id'])
    op.create_index('ix_auction_sales_auction_source', 'auction_sales', ['auction_source'])
    op.create_index('ix_auction_sales_sold_at', 'auction_sales', ['sold_at'])
    op.create_index('ix_auction_sales_created_at', 'auction_sales', ['created_at'])
    op.create_index('ix_auction_sales_vin_source', 'auction_sales', ['vin', 'auction_source'])

    # Create auction_tracking table
    op.create_table(
        'auction_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_url', sa.Text(), nullable=False),
        sa.Column('target_type', sa.String(length=20), nullable=False),
        sa.Column('make', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('page_num', sa.Integer(), nullable=True),
        sa.Column('next_check_at', sa.DateTime(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_http_status', sa.Integer(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_url', name='uq_auction_tracking_target_url')
    )

    # Create indexes for auction_tracking
    op.create_index('ix_auction_tracking_id', 'auction_tracking', ['id'])
    op.create_index('ix_auction_tracking_make', 'auction_tracking', ['make'])
    op.create_index('ix_auction_tracking_model', 'auction_tracking', ['model'])
    op.create_index('ix_auction_tracking_next_check_at', 'auction_tracking', ['next_check_at'])
    op.create_index('ix_auction_tracking_status', 'auction_tracking', ['status'])
    op.create_index('ix_auction_tracking_status_next_check', 'auction_tracking', ['status', 'next_check_at'])


def downgrade() -> None:
    # Drop auction_tracking table and its indexes
    op.drop_index('ix_auction_tracking_status_next_check', table_name='auction_tracking')
    op.drop_index('ix_auction_tracking_status', table_name='auction_tracking')
    op.drop_index('ix_auction_tracking_next_check_at', table_name='auction_tracking')
    op.drop_index('ix_auction_tracking_model', table_name='auction_tracking')
    op.drop_index('ix_auction_tracking_make', table_name='auction_tracking')
    op.drop_index('ix_auction_tracking_id', table_name='auction_tracking')
    op.drop_table('auction_tracking')

    # Drop auction_sales table and its indexes
    op.drop_index('ix_auction_sales_vin_source', table_name='auction_sales')
    op.drop_index('ix_auction_sales_created_at', table_name='auction_sales')
    op.drop_index('ix_auction_sales_sold_at', table_name='auction_sales')
    op.drop_index('ix_auction_sales_auction_source', table_name='auction_sales')
    op.drop_index('ix_auction_sales_lot_id', table_name='auction_sales')
    op.drop_index('ix_auction_sales_vin', table_name='auction_sales')
    op.drop_index('ix_auction_sales_id', table_name='auction_sales')
    op.drop_table('auction_sales')
