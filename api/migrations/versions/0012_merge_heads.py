"""merge heads

Revision ID: 0012_merge_heads
Revises: 0011_alerts_notifications, 0006_provider_settings
Create Date: 2025-12-15
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0012_merge_heads"
down_revision = ("0011_alerts_notifications", "0006_provider_settings")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
