"""add provider_settings table

Revision ID: 0006_provider_settings
Revises: 0005_usage_and_plan_quota
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_provider_settings"
down_revision = "0005_usage_and_plan_quota"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="both"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("key", name="uq_provider_settings_key"),
    )


def downgrade() -> None:
    op.drop_table("provider_settings")
