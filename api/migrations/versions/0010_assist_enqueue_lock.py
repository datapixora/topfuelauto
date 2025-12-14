"""Add enqueue lock to assist cases

Revision ID: 0010_assist_enqueue_lock
Revises: 0009_assist_core_plan_fields
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0010_assist_enqueue_lock"
down_revision = "0009_assist_core_plan_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("assist_cases")}
    if "enqueue_locked_until" not in cols:
        op.add_column("assist_cases", sa.Column("enqueue_locked_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("assist_cases", "enqueue_locked_until")
