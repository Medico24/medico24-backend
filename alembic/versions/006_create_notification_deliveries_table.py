"""create notification_deliveries table

Revision ID: 006
Revises: 005
Create Date: 2026-01-02 12:01:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create notification_deliveries table for tracking per-device delivery status."""
    op.create_table(
        "notification_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("push_token_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fcm_message_id", sa.Text(), nullable=True),
        sa.Column(
            "delivery_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("delivered_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["push_token_id"], ["push_tokens.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "delivery_status IN ('pending', 'sent', 'delivered', 'failed', 'invalid_token')",
            name="notification_deliveries_status_check",
        ),
        sa.UniqueConstraint("notification_id", "push_token_id", name="unique_notification_token"),
    )

    # Create indexes for better query performance
    op.create_index(
        "idx_notification_deliveries_notification",
        "notification_deliveries",
        ["notification_id"],
    )
    op.create_index(
        "idx_notification_deliveries_token", "notification_deliveries", ["push_token_id"]
    )
    op.create_index(
        "idx_notification_deliveries_status",
        "notification_deliveries",
        ["delivery_status"],
    )


def downgrade() -> None:
    """Drop notification_deliveries table."""
    op.drop_index("idx_notification_deliveries_status", table_name="notification_deliveries")
    op.drop_index("idx_notification_deliveries_token", table_name="notification_deliveries")
    op.drop_index("idx_notification_deliveries_notification", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
