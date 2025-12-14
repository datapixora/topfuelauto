"""Add Stripe price ids to plans and billing events table

Revision ID: 0008_plan_stripe_prices
Revises: 0007_user_current_plan
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0008_plan_stripe_prices"
down_revision = "0007_user_current_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    plan_cols = {c["name"] for c in insp.get_columns("plans")}
    if "stripe_price_id_monthly" not in plan_cols:
        op.add_column("plans", sa.Column("stripe_price_id_monthly", sa.String(length=100), nullable=True))
    if "stripe_price_id_yearly" not in plan_cols:
        op.add_column("plans", sa.Column("stripe_price_id_yearly", sa.String(length=100), nullable=True))

    if not insp.has_table("billing_events"):
        op.create_table(
            "billing_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("stripe_event_id", sa.String(length=255), nullable=False, unique=True),
            sa.Column("type", sa.String(length=100), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_column("plans", "stripe_price_id_yearly")
    op.drop_column("plans", "stripe_price_id_monthly")
