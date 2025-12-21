"""Add proxy health tracking fields

Revision ID: 0032_proxy_health_tracking
Revises: 0031_proxy_unhealthy_until
Create Date: 2025-12-21 12:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0032_proxy_health_tracking"
down_revision = "0031_proxy_unhealthy_until"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use longer timeout for production deployments where table may be under load
    op.execute("SET lock_timeout = '30s'")
    op.execute("SET statement_timeout = '120s'")

    # Add consecutive_failures for tracking failure streaks
    # Use nullable first to avoid table rewrite, then set default
    op.add_column("proxies", sa.Column("consecutive_failures", sa.Integer, nullable=True))
    op.execute("UPDATE proxies SET consecutive_failures = 0 WHERE consecutive_failures IS NULL")
    op.alter_column("proxies", "consecutive_failures", nullable=False, server_default="0")

    # Add banned_until for permanent/long-term bans
    op.add_column("proxies", sa.Column("banned_until", sa.DateTime(timezone=True), nullable=True))

    # Add last_failure_at to track when proxy last failed
    op.add_column("proxies", sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.execute("SET lock_timeout = '30s'")
    op.execute("SET statement_timeout = '120s'")

    op.drop_column("proxies", "last_failure_at")
    op.drop_column("proxies", "banned_until")
    op.drop_column("proxies", "consecutive_failures")
