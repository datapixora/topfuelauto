"""Add current_plan_id to users

Revision ID: 0007_user_current_plan
Revises: 0006_user_active_admin_log
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0007_user_current_plan"
down_revision = "0006_user_active_admin_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("users")}
    if "current_plan_id" not in cols:
        op.add_column("users", sa.Column("current_plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "current_plan_id")
