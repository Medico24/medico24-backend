"""create notifications table

Revision ID: 005
Revises: 004
Create Date: 2026-01-02 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create notifications table for tracking sent push notifications."""
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'normal'"),
        ),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("delivered_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("read_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("scheduled_for", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "notification_type IN ('appointment_reminder', 'appointment_confirmation', "
            "'appointment_cancelled', 'prescription_ready', 'pharmacy_update', "
            "'system_announcement', 'other')",
            name="notifications_type_check",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="notifications_priority_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'failed', 'read')",
            name="notifications_status_check",
        ),
    )

    # Create indexes for better query performance
    op.create_index("idx_notifications_user_id", "notifications", ["user_id"])
    op.create_index("idx_notifications_status", "notifications", ["status"])
    op.create_index("idx_notifications_created_at", "notifications", [sa.text("created_at DESC")])
    op.create_index("idx_notifications_user_status", "notifications", ["user_id", "status"])
    op.create_index("idx_notifications_type", "notifications", ["notification_type"])
    op.create_index(
        "idx_notifications_scheduled",
        "notifications",
        ["scheduled_for"],
        postgresql_where=sa.text("scheduled_for IS NOT NULL"),
    )
    op.create_index(
        "idx_notifications_expires",
        "notifications",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop notifications table."""
    op.drop_index("idx_notifications_expires", table_name="notifications")
    op.drop_index("idx_notifications_scheduled", table_name="notifications")
    op.drop_index("idx_notifications_type", table_name="notifications")
    op.drop_index("idx_notifications_user_status", table_name="notifications")
    op.drop_index("idx_notifications_created_at", table_name="notifications")
    op.drop_index("idx_notifications_status", table_name="notifications")
    op.drop_index("idx_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
