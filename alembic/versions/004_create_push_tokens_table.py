"""create push_tokens table

Revision ID: 004
Revises: 003
Create Date: 2026-01-02 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create push_tokens table for FCM push notification tokens."""
    op.create_table(
        "push_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fcm_token", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "platform IN ('android', 'ios', 'web')", name="push_tokens_platform_check"
        ),
        sa.UniqueConstraint("user_id", "fcm_token", name="unique_user_fcm_token"),
    )

    # Create indexes for better query performance
    op.create_index("idx_push_tokens_user_id", "push_tokens", ["user_id"])
    op.create_index("idx_push_tokens_is_active", "push_tokens", ["is_active"])


def downgrade() -> None:
    """Drop push_tokens table."""
    op.drop_index("idx_push_tokens_is_active", table_name="push_tokens")
    op.drop_index("idx_push_tokens_user_id", table_name="push_tokens")
    op.drop_table("push_tokens")
