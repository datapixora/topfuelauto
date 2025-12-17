"""Add public pricing fields to plans

Revision ID: 0025_public_plans_fields
Revises: 0024_admin_imports
Create Date: 2025-12-17
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0025_public_plans_fields"
down_revision = "0024_admin_imports"
branch_labels = None
depends_on = None


FEATURE_LABELS = {
    "vin_history": "VIN history access",
    "priority_support": "Priority support",
    "bulk": "Bulk tools",
    "vin_decode": "VIN decode",
}


def _normalize_features(value):
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out
    if isinstance(value, dict):
        out = []
        for k, enabled in value.items():
            if enabled:
                key = str(k)
                out.append(FEATURE_LABELS.get(key, key))
        return out
    return []


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    plan_cols = {c["name"] for c in insp.get_columns("plans")}
    plan_indexes = {i["name"] for i in insp.get_indexes("plans")}

    if "slug" not in plan_cols:
        op.add_column("plans", sa.Column("slug", sa.String(length=50), nullable=True))

    if "is_featured" not in plan_cols:
        op.add_column(
            "plans",
            sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    if "sort_order" not in plan_cols:
        op.add_column(
            "plans",
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )

    # Backfill slug from existing key values.
    op.execute("UPDATE plans SET slug = key WHERE (slug IS NULL OR slug = '') AND key IS NOT NULL")
    op.alter_column("plans", "slug", nullable=False)

    if "ix_plans_slug" not in plan_indexes:
        op.create_index("ix_plans_slug", "plans", ["slug"], unique=True)

    # Optional: enforce at most one featured plan at the DB level.
    if "uq_plans_featured_true" not in plan_indexes:
        # Ensure at most one plan is featured before the unique index is created.
        op.execute("""
            UPDATE plans
            SET is_featured = false
            WHERE is_featured IS true
              AND id <> (
                SELECT id
                FROM plans
                WHERE is_featured IS true
                ORDER BY sort_order ASC, created_at ASC, id ASC
                LIMIT 1
              )
        """)
        op.create_index(
            "uq_plans_featured_true",
            "plans",
            ["is_featured"],
            unique=True,
            postgresql_where=sa.text("is_featured"),
        )

    # Ensure features is a JSON array of strings by default.
    if "features" in plan_cols:
        # Ensure existing NULLs become [] so the public endpoint is deterministic.
        op.execute("UPDATE plans SET features = '[]'::jsonb WHERE features IS NULL")

        # Convert legacy feature objects (dict) into a list of enabled feature labels.
        rows = bind.execute(sa.text("SELECT id, features FROM plans")).fetchall()
        for row in rows:
            feats = row[1]
            normalized = _normalize_features(feats)
            if normalized != feats:
                bind.execute(
                    sa.text("UPDATE plans SET features = :features::jsonb WHERE id = :id"),
                    {"id": row[0], "features": json.dumps(normalized)},
                )

        # Set server default to [] for new rows.
        op.alter_column("plans", "features", server_default=sa.text("'[]'::jsonb"), nullable=False)


def downgrade() -> None:
    # Best-effort downgrade (does not attempt to restore legacy feature objects).
    op.drop_index("uq_plans_featured_true", table_name="plans")
    op.drop_index("ix_plans_slug", table_name="plans")
    op.drop_column("plans", "sort_order")
    op.drop_column("plans", "is_featured")
    op.drop_column("plans", "slug")
