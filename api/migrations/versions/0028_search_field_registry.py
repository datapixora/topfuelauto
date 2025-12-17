"""Add search field registry and JSONB extra storage

Revision ID: 0028_search_field_registry
Revises: 0027_merge_heads
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0028_search_field_registry'
down_revision = '0027_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add search_fields table and JSONB columns to merged_listings."""

    # Add extra and raw_payload JSONB columns to merged_listings
    op.add_column('merged_listings', sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('merged_listings', sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Create GIN index on extra column for fast JSONB queries
    op.create_index('ix_merged_listings_extra_gin', 'merged_listings', ['extra'], postgresql_using='gin')

    # Create search_fields table
    op.create_table(
        'search_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('storage', sa.String(length=20), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('filterable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sortable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('visible_in_search', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('visible_in_results', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ui_widget', sa.String(length=50), nullable=True),
        sa.Column('source_aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('normalization', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_search_fields_key', 'search_fields', ['key'], unique=True)
    op.create_index('ix_search_fields_enabled', 'search_fields', ['enabled'])

    # Seed core fields
    op.execute("""
        INSERT INTO search_fields (key, label, data_type, storage, enabled, filterable, sortable, visible_in_search, visible_in_results, source_aliases) VALUES
        ('year', 'Year', 'integer', 'core', true, true, true, true, true, '["year", "Year", "YEAR"]'),
        ('make', 'Make', 'string', 'core', true, true, true, true, true, '["make", "Make", "MAKE", "manufacturer", "Manufacturer"]'),
        ('model', 'Model', 'string', 'core', true, true, true, true, true, '["model", "Model", "MODEL"]'),
        ('price', 'Price', 'decimal', 'core', true, true, true, true, true, '["price", "Price", "PRICE", "current_bid", "Current Bid"]'),
        ('mileage', 'Mileage', 'integer', 'core', true, true, true, true, true, '["mileage", "Mileage", "MILEAGE", "odometer", "Odometer"]'),
        ('location', 'Location', 'string', 'core', true, true, false, true, true, '["location", "Location", "LOCATION", "sale_name", "Sale Name"]'),
        ('vin', 'VIN', 'string', 'extra', true, true, false, true, true, '["vin", "VIN", "Vin"]'),
        ('damage', 'Damage', 'string', 'extra', true, true, false, true, true, '["damage", "Damage", "DAMAGE", "damage_description", "Damage Description"]'),
        ('title_code', 'Title Code', 'string', 'extra', true, true, false, true, true, '["title_code", "Title Code", "title_status", "Title Status"]'),
        ('cylinders', 'Cylinders', 'integer', 'extra', true, true, true, true, true, '["cylinders", "Cylinders", "CYLINDERS", "Cylinder", "cylinder"]'),
        ('transmission', 'Transmission', 'string', 'extra', true, true, true, true, true, '["transmission", "Transmission", "TRANSMISSION"]'),
        ('fuel_type', 'Fuel Type', 'string', 'extra', true, true, true, true, true, '["fuel_type", "Fuel Type", "fuel", "Fuel"]'),
        ('body_style', 'Body Style', 'string', 'extra', true, true, true, true, true, '["body_style", "Body Style", "body", "Body"]'),
        ('color', 'Color', 'string', 'extra', true, true, true, true, true, '["color", "Color", "COLOR", "exterior_color", "Exterior Color"]')
    """)


def downgrade() -> None:
    """Remove search field registry and JSONB columns."""

    op.drop_index('ix_search_fields_enabled', table_name='search_fields')
    op.drop_index('ix_search_fields_key', table_name='search_fields')
    op.drop_table('search_fields')

    op.drop_index('ix_merged_listings_extra_gin', table_name='merged_listings', postgresql_using='gin')
    op.drop_column('merged_listings', 'raw_payload')
    op.drop_column('merged_listings', 'extra')
