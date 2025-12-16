"""add provider settings json config

Revision ID: 0015_provider_settings_config
Revises: 0014_on_demand_crawl
Create Date: 2025-12-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0015_provider_settings_config"
down_revision = "0014_on_demand_crawl"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_settings",
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("provider_settings", "settings_json")

