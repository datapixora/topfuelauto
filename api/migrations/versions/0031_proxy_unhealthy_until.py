"""Add unhealthy_until to proxies

Revision ID: 0031_proxy_unhealthy_until
Revises: 0030_bidfax_proxy_fields
Create Date: 2025-12-18 23:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0031_proxy_unhealthy_until"
down_revision = "0030_bidfax_proxy_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '5s'")
    op.execute("SET statement_timeout = '60s'")
    op.add_column("proxies", sa.Column("unhealthy_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.execute("SET lock_timeout = '5s'")
    op.execute("SET statement_timeout = '60s'")
    op.drop_column("proxies", "unhealthy_until")
