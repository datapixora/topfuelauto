"""Add proxy fields to auction_tracking for Bidfax

Revision ID: 0030_bidfax_proxy_fields
Revises: 0029_auction_sales_tracking
Create Date: 2025-12-18 18:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0030_bidfax_proxy_fields"
down_revision = "0029_auction_sales_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("auction_tracking", sa.Column("proxy_id", sa.Integer(), nullable=True))
    op.add_column("auction_tracking", sa.Column("proxy_exit_ip", sa.String(length=64), nullable=True))
    op.add_column("auction_tracking", sa.Column("proxy_error", sa.Text(), nullable=True))
    op.create_index("ix_auction_tracking_proxy_id", "auction_tracking", ["proxy_id"], unique=False)
    op.create_foreign_key(
        "fk_auction_tracking_proxy",
        "auction_tracking",
        "proxies",
        ["proxy_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_auction_tracking_proxy", "auction_tracking", type_="foreignkey")
    op.drop_index("ix_auction_tracking_proxy_id", table_name="auction_tracking")
    op.drop_column("auction_tracking", "proxy_error")
    op.drop_column("auction_tracking", "proxy_exit_ip")
    op.drop_column("auction_tracking", "proxy_id")
