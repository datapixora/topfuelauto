"""add search cache entries

Revision ID: 0013_search_cache_entries
Revises: 0012_merge_heads
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0013_search_cache_entries"
down_revision = "0012_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_cache_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signature", sa.String(length=255), nullable=False),
        sa.Column("providers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("query_normalized", sa.String(length=255), nullable=True),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("limit", sa.Integer(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("results_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("signature", name="uq_search_cache_signature"),
    )


def downgrade() -> None:
    op.drop_table("search_cache_entries")
