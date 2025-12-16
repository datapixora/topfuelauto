"""add on-demand crawl search jobs/results

Revision ID: 0014_on_demand_crawl
Revises: 0013_search_cache_entries
Create Date: 2025-12-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0014_on_demand_crawl"
down_revision = "0013_search_cache_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("query_normalized", sa.String(length=255), nullable=False),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_search_jobs_user_id", "search_jobs", ["user_id"])
    op.create_index("ix_search_jobs_status", "search_jobs", ["status"])

    op.create_table(
        "search_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("search_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("make", sa.String(length=80), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("extra_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_search_results_job_id", "search_results", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_search_results_job_id", table_name="search_results")
    op.drop_table("search_results")
    op.drop_index("ix_search_jobs_status", table_name="search_jobs")
    op.drop_index("ix_search_jobs_user_id", table_name="search_jobs")
    op.drop_table("search_jobs")

