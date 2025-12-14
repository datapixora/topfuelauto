"""Assist core tables and plan assist fields

Revision ID: 0009_assist_core_plan_fields
Revises: 0008_plan_stripe_prices
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0009_assist_core_plan_fields"
down_revision = "0008_plan_stripe_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    plan_cols = {c["name"] for c in insp.get_columns("plans")}
    new_plan_cols = {
        "assist_one_shot_per_day": sa.Column("assist_one_shot_per_day", sa.Integer(), nullable=True),
        "assist_watch_enabled": sa.Column("assist_watch_enabled", sa.Boolean(), nullable=True, server_default=sa.false()),
        "assist_watch_max_cases": sa.Column("assist_watch_max_cases", sa.Integer(), nullable=True),
        "assist_watch_runs_per_day": sa.Column("assist_watch_runs_per_day", sa.Integer(), nullable=True),
        "assist_ai_budget_cents_per_day": sa.Column("assist_ai_budget_cents_per_day", sa.Integer(), nullable=True),
        "assist_reruns_per_day": sa.Column("assist_reruns_per_day", sa.Integer(), nullable=True),
    }
    for name, col in new_plan_cols.items():
        if name not in plan_cols:
            op.add_column("plans", col)
            if col.server_default is not None:
                op.execute(f"ALTER TABLE plans ALTER COLUMN {name} DROP DEFAULT")

    if not insp.has_table("assist_cases"):
        op.create_table(
            "assist_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("mode", sa.String(length=16), nullable=False, server_default="one_shot"),
            sa.Column("intake_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("intake_payload", sa.JSON(), nullable=True),
            sa.Column("normalized_payload", sa.JSON(), nullable=True),
            sa.Column("last_run_at", sa.DateTime(), nullable=True),
            sa.Column("next_run_at", sa.DateTime(), nullable=True),
            sa.Column("runs_today", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_allowed_run_at", sa.DateTime(), nullable=True),
            sa.Column("budget_cents_limit", sa.Integer(), nullable=True),
            sa.Column("budget_cents_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not insp.has_table("assist_steps"):
        op.create_table(
            "assist_steps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("assist_cases.id"), nullable=False),
            sa.Column("step_key", sa.String(length=100), nullable=False),
            sa.Column("step_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("provider", sa.String(length=100), nullable=True),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("input_json", sa.JSON(), nullable=True),
            sa.Column("output_json", sa.JSON(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("token_in", sa.Integer(), nullable=True),
            sa.Column("token_out", sa.Integer(), nullable=True),
            sa.Column("cost_cents", sa.Integer(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not insp.has_table("assist_artifacts"):
        op.create_table(
            "assist_artifacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), sa.ForeignKey("assist_cases.id"), nullable=False),
            sa.Column("type", sa.String(length=100), nullable=False),
            sa.Column("content_text", sa.Text(), nullable=True),
            sa.Column("content_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not insp.has_table("prompt_templates"):
        op.create_table(
            "prompt_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(length=255), nullable=False, unique=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("template", sa.Text(), nullable=False),
            sa.Column("schema_json", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("prompt_templates")
    op.drop_table("assist_artifacts")
    op.drop_table("assist_steps")
    op.drop_table("assist_cases")
    op.drop_column("plans", "assist_reruns_per_day")
    op.drop_column("plans", "assist_ai_budget_cents_per_day")
    op.drop_column("plans", "assist_watch_runs_per_day")
    op.drop_column("plans", "assist_watch_max_cases")
    op.drop_column("plans", "assist_watch_enabled")
    op.drop_column("plans", "assist_one_shot_per_day")
