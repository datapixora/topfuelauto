"""Add admin_imports table for CSV upload feature

Revision ID: 0024_admin_imports
Revises: 0023_fix_cascade
Create Date: 2025-12-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, BYTEA

revision = "0024_admin_imports"
down_revision = "0023_fix_cascade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create admin_imports table for CSV upload/import tracking.
    """
    # Create ImportStatus enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE importstatus AS ENUM ('UPLOADED', 'PARSING', 'READY', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create admin_imports table
    op.create_table(
        "admin_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(100), nullable=True),  # Optional source identifier (e.g., "copart_manual")
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),  # For deduplication
        sa.Column("file_data", BYTEA, nullable=True),  # Store file bytes (for modest files)

        # Status tracking
        sa.Column("status", sa.String(20), nullable=False, default="UPLOADED", index=True),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("processed_rows", sa.Integer(), nullable=False, default=0),
        sa.Column("created_count", sa.Integer(), nullable=False, default=0),
        sa.Column("updated_count", sa.Integer(), nullable=False, default=0),
        sa.Column("skipped_count", sa.Integer(), nullable=False, default=0),
        sa.Column("error_count", sa.Integer(), nullable=False, default=0),

        # CSV structure and mapping
        sa.Column("detected_headers", JSONB, nullable=True),  # ["Lot URL", "Year", "Make", ...]
        sa.Column("column_map", JSONB, nullable=True),  # {"Lot URL": "url", "Year": "year", ...}
        sa.Column("sample_preview", JSONB, nullable=True),  # First 20 rows as array of objects

        # Error tracking
        sa.Column("error_log", sa.Text(), nullable=True),  # Newline-separated errors or JSON array
        sa.Column("error_details", JSONB, nullable=True),  # Structured error info

        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes
    op.create_index("ix_admin_imports_created_at", "admin_imports", ["created_at"])
    op.create_index("ix_admin_imports_source_key", "admin_imports", ["source_key"])


def downgrade() -> None:
    """Drop admin_imports table."""
    op.drop_index("ix_admin_imports_source_key", "admin_imports")
    op.drop_index("ix_admin_imports_created_at", "admin_imports")
    op.drop_table("admin_imports")
    op.execute("DROP TYPE IF EXISTS importstatus")
