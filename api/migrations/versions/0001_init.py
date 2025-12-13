"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2025-12-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_pro', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=False)

    op.create_table(
        'vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('make', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('trim', sa.String(length=100), nullable=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vehicles_make', 'vehicles', ['make'], unique=False)
    op.create_index('ix_vehicles_model', 'vehicles', ['model'], unique=False)
    op.create_index('ix_vehicles_year', 'vehicles', ['year'], unique=False)

    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True, server_default='internal'),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True, server_default='USD'),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('condition', sa.String(length=50), nullable=True),
        sa.Column('transmission', sa.String(length=50), nullable=True),
        sa.Column('mileage', sa.Integer(), nullable=True),
        sa.Column('risk_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column('search_text', sa.Text(), nullable=True),
        sa.Column('search_tsv', postgresql.TSVECTOR(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_listings_title', 'listings', ['title'], unique=False)
    op.create_index('ix_listings_vehicle', 'listings', ['vehicle_id'], unique=False)
    op.create_index('ix_listings_search_tsv', 'listings', ['search_tsv'], unique=False, postgresql_using='gin')
    op.create_index('ix_listings_search_text_trgm', 'listings', ['search_text'], unique=False, postgresql_using='gin', postgresql_ops={'search_text': 'gin_trgm_ops'})

    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True, server_default='USD'),
        sa.Column('ts', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'broker_leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('max_bid', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('destination_country', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='NEW'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'vin_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vin', sa.String(length=32), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vin_reports_vin', 'vin_reports', ['vin'], unique=False)


def downgrade():
    op.drop_index('ix_vin_reports_vin', table_name='vin_reports')
    op.drop_table('vin_reports')
    op.drop_table('broker_leads')
    op.drop_table('price_history')
    op.drop_index('ix_listings_search_text_trgm', table_name='listings')
    op.drop_index('ix_listings_search_tsv', table_name='listings')
    op.drop_index('ix_listings_vehicle', table_name='listings')
    op.drop_index('ix_listings_title', table_name='listings')
    op.drop_table('listings')
    op.drop_index('ix_vehicles_year', table_name='vehicles')
    op.drop_index('ix_vehicles_model', table_name='vehicles')
    op.drop_index('ix_vehicles_make', table_name='vehicles')
    op.drop_table('vehicles')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')