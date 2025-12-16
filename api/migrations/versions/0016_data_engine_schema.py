"""Add Data Engine schema for admin-controlled scraping

Revision ID: 0016_data_engine_schema
Revises: 0015_provider_settings_config
Create Date: 2025-12-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0016_data_engine_schema"
down_revision = "0015_provider_settings_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_sources table
    op.create_table(
        "admin_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="list_only"),
        sa.Column("schedule_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_items_per_run", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("max_pages_per_run", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("rate_per_minute", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("concurrency", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disabled_reason", sa.Text(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_sources_id"), "admin_sources", ["id"], unique=False)
    op.create_index(op.f("ix_admin_sources_key"), "admin_sources", ["key"], unique=True)
    op.create_index("ix_admin_sources_enabled_next_run", "admin_sources", ["is_enabled", "next_run_at"], unique=False)

    # Create admin_runs table
    op.create_table(
        "admin_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("pages_planned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_staged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("debug_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_id"], ["admin_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_runs_id"), "admin_runs", ["id"], unique=False)
    op.create_index(op.f("ix_admin_runs_source_id"), "admin_runs", ["source_id"], unique=False)
    op.create_index(op.f("ix_admin_runs_status"), "admin_runs", ["status"], unique=False)
    op.create_index(op.f("ix_admin_runs_created_at"), "admin_runs", ["created_at"], unique=False)
    op.create_index("ix_admin_runs_source_created", "admin_runs", ["source_id", "created_at"], unique=False)

    # Create staged_listings table
    op.create_table(
        "staged_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("source_listing_id", sa.String(length=255), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("make", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True, server_default="USD"),
        sa.Column("odometer_value", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("listed_at", sa.DateTime(), nullable=True),
        sa.Column("sale_datetime", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["admin_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", "canonical_url", name="uq_staged_listing_source_url"),
    )
    op.create_index(op.f("ix_staged_listings_id"), "staged_listings", ["id"], unique=False)
    op.create_index(op.f("ix_staged_listings_run_id"), "staged_listings", ["run_id"], unique=False)
    op.create_index(op.f("ix_staged_listings_source_key"), "staged_listings", ["source_key"], unique=False)
    op.create_index(op.f("ix_staged_listings_year"), "staged_listings", ["year"], unique=False)
    op.create_index(op.f("ix_staged_listings_make"), "staged_listings", ["make"], unique=False)
    op.create_index(op.f("ix_staged_listings_model"), "staged_listings", ["model"], unique=False)
    op.create_index("ix_staged_listings_run_created", "staged_listings", ["run_id", "created_at"], unique=False)

    # Create staged_listing_attributes table
    op.create_table(
        "staged_listing_attributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staged_listing_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_num", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["staged_listing_id"], ["staged_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staged_listing_attributes_id"), "staged_listing_attributes", ["id"], unique=False)
    op.create_index(op.f("ix_staged_listing_attributes_staged_listing_id"), "staged_listing_attributes", ["staged_listing_id"], unique=False)
    op.create_index("ix_staged_attributes_listing_key", "staged_listing_attributes", ["staged_listing_id", "key"], unique=False)

    # Create merged_listings table
    op.create_table(
        "merged_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("source_listing_id", sa.String(length=255), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("make", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True, server_default="USD"),
        sa.Column("odometer_value", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("listed_at", sa.DateTime(), nullable=True),
        sa.Column("sale_datetime", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("merged_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", "canonical_url", name="uq_merged_listing_source_url"),
    )
    op.create_index(op.f("ix_merged_listings_id"), "merged_listings", ["id"], unique=False)
    op.create_index(op.f("ix_merged_listings_source_key"), "merged_listings", ["source_key"], unique=False)
    op.create_index(op.f("ix_merged_listings_year"), "merged_listings", ["year"], unique=False)
    op.create_index(op.f("ix_merged_listings_make"), "merged_listings", ["make"], unique=False)
    op.create_index(op.f("ix_merged_listings_model"), "merged_listings", ["model"], unique=False)
    op.create_index(op.f("ix_merged_listings_merged_at"), "merged_listings", ["merged_at"], unique=False)

    # Create merged_listing_attributes table
    op.create_table(
        "merged_listing_attributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_num", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["listing_id"], ["merged_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_merged_listing_attributes_id"), "merged_listing_attributes", ["id"], unique=False)
    op.create_index(op.f("ix_merged_listing_attributes_listing_id"), "merged_listing_attributes", ["listing_id"], unique=False)
    op.create_index("ix_merged_attributes_listing_key", "merged_listing_attributes", ["listing_id", "key"], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_index("ix_merged_attributes_listing_key", table_name="merged_listing_attributes")
    op.drop_index(op.f("ix_merged_listing_attributes_listing_id"), table_name="merged_listing_attributes")
    op.drop_index(op.f("ix_merged_listing_attributes_id"), table_name="merged_listing_attributes")
    op.drop_table("merged_listing_attributes")

    op.drop_index(op.f("ix_merged_listings_merged_at"), table_name="merged_listings")
    op.drop_index(op.f("ix_merged_listings_model"), table_name="merged_listings")
    op.drop_index(op.f("ix_merged_listings_make"), table_name="merged_listings")
    op.drop_index(op.f("ix_merged_listings_year"), table_name="merged_listings")
    op.drop_index(op.f("ix_merged_listings_source_key"), table_name="merged_listings")
    op.drop_index(op.f("ix_merged_listings_id"), table_name="merged_listings")
    op.drop_table("merged_listings")

    op.drop_index("ix_staged_attributes_listing_key", table_name="staged_listing_attributes")
    op.drop_index(op.f("ix_staged_listing_attributes_staged_listing_id"), table_name="staged_listing_attributes")
    op.drop_index(op.f("ix_staged_listing_attributes_id"), table_name="staged_listing_attributes")
    op.drop_table("staged_listing_attributes")

    op.drop_index("ix_staged_listings_run_created", table_name="staged_listings")
    op.drop_index(op.f("ix_staged_listings_model"), table_name="staged_listings")
    op.drop_index(op.f("ix_staged_listings_make"), table_name="staged_listings")
    op.drop_index(op.f("ix_staged_listings_year"), table_name="staged_listings")
    op.drop_index(op.f("ix_staged_listings_source_key"), table_name="staged_listings")
    op.drop_index(op.f("ix_staged_listings_run_id"), table_name="staged_listings")
    op.drop_index(op.f("ix_staged_listings_id"), table_name="staged_listings")
    op.drop_table("staged_listings")

    op.drop_index("ix_admin_runs_source_created", table_name="admin_runs")
    op.drop_index(op.f("ix_admin_runs_created_at"), table_name="admin_runs")
    op.drop_index(op.f("ix_admin_runs_status"), table_name="admin_runs")
    op.drop_index(op.f("ix_admin_runs_source_id"), table_name="admin_runs")
    op.drop_index(op.f("ix_admin_runs_id"), table_name="admin_runs")
    op.drop_table("admin_runs")

    op.drop_index("ix_admin_sources_enabled_next_run", table_name="admin_sources")
    op.drop_index(op.f("ix_admin_sources_key"), table_name="admin_sources")
    op.drop_index(op.f("ix_admin_sources_id"), table_name="admin_sources")
    op.drop_table("admin_sources")
