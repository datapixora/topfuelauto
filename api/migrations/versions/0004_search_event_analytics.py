"""Add analytics fields to search_events

Revision ID: 0004_search_event_analytics
Revises: 0003_plans
Create Date: 2025-12-14 12:50:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0004_search_event_analytics"
down_revision = "0003_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    existing_cols = {col["name"] for col in insp.get_columns("search_events")}
    existing_indexes = {ix["name"] for ix in insp.get_indexes("search_events")}

    def add_col(name: str, column: sa.Column):
        if name not in existing_cols:
            op.add_column("search_events", column)

    add_col("session_id", sa.Column("session_id", sa.String(length=64), nullable=True))
    add_col("query_raw", sa.Column("query_raw", sa.String(length=255), nullable=True))
    add_col("query_normalized", sa.Column("query_normalized", sa.String(length=255), nullable=True))
    add_col("filters_json", sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    add_col("providers", sa.Column("providers", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    add_col("result_count", sa.Column("result_count", sa.Integer(), nullable=True))
    add_col(
        "cache_hit",
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    add_col(
        "rate_limited",
        sa.Column("rate_limited", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    add_col(
        "status",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ok"),
    )
    add_col("error_code", sa.Column("error_code", sa.String(length=50), nullable=True))

    if "ix_search_events_created_at" not in existing_indexes:
        op.create_index("ix_search_events_created_at", "search_events", ["created_at"], unique=False)
    if "ix_search_events_query_normalized" not in existing_indexes:
        op.create_index("ix_search_events_query_normalized", "search_events", ["query_normalized"], unique=False)
    if "ix_search_events_session_id" not in existing_indexes:
        op.create_index("ix_search_events_session_id", "search_events", ["session_id"], unique=False)
    if "ix_search_events_ts_querynorm" not in existing_indexes:
        op.create_index(
            "ix_search_events_ts_querynorm", "search_events", ["created_at", "query_normalized"], unique=False
        )


def downgrade() -> None:
    op.drop_index("ix_search_events_ts_querynorm", table_name="search_events")
    op.drop_index("ix_search_events_session_id", table_name="search_events")
    op.drop_index("ix_search_events_query_normalized", table_name="search_events")
    op.drop_index("ix_search_events_created_at", table_name="search_events")

    op.drop_column("search_events", "error_code")
    op.drop_column("search_events", "status")
    op.drop_column("search_events", "rate_limited")
    op.drop_column("search_events", "cache_hit")
    op.drop_column("search_events", "result_count")
    op.drop_column("search_events", "providers")
    op.drop_column("search_events", "filters_json")
    op.drop_column("search_events", "query_normalized")
    op.drop_column("search_events", "query_raw")
    op.drop_column("search_events", "session_id")
