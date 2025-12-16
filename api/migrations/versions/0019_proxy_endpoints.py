"""Add proxies table and run proxy fields

Revision ID: 0019_proxy_endpoints
Revises: 0018_data_engine_block_cooldown
Create Date: 2025-12-16 18:28:05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0019_proxy_endpoints"
down_revision = "0018_data_engine_block_cooldown"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proxies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="3120"),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("scheme", sa.String(length=10), nullable=False, server_default="http"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_concurrency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("last_check_at", sa.DateTime(), nullable=True),
        sa.Column("last_check_status", sa.String(length=10), nullable=True),
        sa.Column("last_exit_ip", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proxies_id"), "proxies", ["id"], unique=False)
    op.create_index("ix_proxies_enabled", "proxies", ["is_enabled"], unique=False)

    # admin_runs proxy fields
    op.add_column("admin_runs", sa.Column("proxy_id", sa.Integer(), nullable=True))
    op.add_column("admin_runs", sa.Column("proxy_exit_ip", sa.String(length=64), nullable=True))
    op.add_column("admin_runs", sa.Column("proxy_error", sa.Text(), nullable=True))
    op.create_foreign_key("fk_admin_runs_proxy", "admin_runs", "proxies", ["proxy_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_admin_runs_proxy", "admin_runs", type_="foreignkey")
    op.drop_column("admin_runs", "proxy_error")
    op.drop_column("admin_runs", "proxy_exit_ip")
    op.drop_column("admin_runs", "proxy_id")

    op.drop_index("ix_proxies_enabled", table_name="proxies")
    op.drop_index(op.f("ix_proxies_id"), table_name="proxies")
    op.drop_table("proxies")
