"""Add daily usage table and plan quota fields

Revision ID: 0005_usage_and_plan_quota
Revises: 0004_search_event_analytics
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0005_usage_and_plan_quota"
down_revision = "0004_search_event_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    plan_cols = {c["name"] for c in insp.get_columns("plans")}

    if "searches_per_day" not in plan_cols:
        op.add_column("plans", sa.Column("searches_per_day", sa.Integer(), nullable=True))
    if "quota_reached_message" not in plan_cols:
        op.add_column("plans", sa.Column("quota_reached_message", sa.Text(), nullable=True))

    if not insp.has_table("daily_usage"):
        op.create_table(
            "daily_usage",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("usage_date", sa.Date(), nullable=False),
            sa.Column("search_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "usage_date", name="uq_daily_usage_user_date"),
        )


def downgrade() -> None:
    op.drop_table("daily_usage")
    op.drop_column("plans", "quota_reached_message")
    op.drop_column("plans", "searches_per_day")
