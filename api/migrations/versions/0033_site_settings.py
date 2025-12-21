"""Add site_settings table

Revision ID: 0033_site_settings
Revises: 0032_proxy_health_tracking
Create Date: 2025-12-21 15:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0033_site_settings"
down_revision = "0032_proxy_health_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("key", sa.String, nullable=False, unique=True, index=True),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("site_settings")
