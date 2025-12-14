"""Add saved search alerts, matches, notifications, and alert plan fields"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0011_alerts_notifications"
down_revision = "0010_assist_enqueue_lock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plan fields for alerts
    op.add_column("plans", sa.Column("alerts_enabled", sa.Boolean(), nullable=True))
    op.add_column("plans", sa.Column("alerts_max_active", sa.Integer(), nullable=True))
    op.add_column("plans", sa.Column("alerts_cadence_minutes", sa.Integer(), nullable=True))

    op.create_table(
        "saved_search_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("query_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("cadence_minutes", sa.Integer(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_result_hash", sa.String(length=128), nullable=True),
        sa.Column("enqueue_locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_search_alerts_user_id", "saved_search_alerts", ["user_id"], unique=False)
    op.create_index("ix_saved_search_alerts_next_run_at", "saved_search_alerts", ["next_run_at"], unique=False)

    op.create_table(
        "alert_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.String(length=128), nullable=False),
        sa.Column("listing_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("matched_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["saved_search_alerts.id"], ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_matches_alert_id", "alert_matches", ["alert_id"], unique=False)
    op.create_index("ix_alert_matches_user_id", "alert_matches", ["user_id"], unique=False)
    op.create_index("ix_alert_matches_matched_at", "alert_matches", ["matched_at"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_alert_matches_matched_at", table_name="alert_matches")
    op.drop_index("ix_alert_matches_user_id", table_name="alert_matches")
    op.drop_index("ix_alert_matches_alert_id", table_name="alert_matches")
    op.drop_table("alert_matches")

    op.drop_index("ix_saved_search_alerts_next_run_at", table_name="saved_search_alerts")
    op.drop_index("ix_saved_search_alerts_user_id", table_name="saved_search_alerts")
    op.drop_table("saved_search_alerts")

    op.drop_column("plans", "alerts_cadence_minutes")
    op.drop_column("plans", "alerts_max_active")
    op.drop_column("plans", "alerts_enabled")
