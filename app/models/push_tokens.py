"""Push tokens model definition using SQLAlchemy Core."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

metadata = MetaData()

push_tokens = Table(
    "push_tokens",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("fcm_token", Text, nullable=False),
    Column("platform", String(10), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true"), index=True),
    Column("last_used_at", TIMESTAMP(timezone=True), nullable=True),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    ),
    CheckConstraint(
        "platform IN ('android', 'ios', 'web')",
        name="push_tokens_platform_check",
    ),
)
