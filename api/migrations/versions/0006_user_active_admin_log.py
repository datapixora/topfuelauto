"""Add user is_active and admin action log

Revision ID: 0006_user_active_admin_log
Revises: 0005_usage_and_plan_quota
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0006_user_active_admin_log"
down_revision = "0005_usage_and_plan_quota"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "is_active" not in user_cols:
        op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        op.execute("ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT")

    if not insp.has_table("admin_action_logs"):
        op.create_table(
            "admin_action_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("admin_action_logs")
    op.drop_column("users", "is_active")
