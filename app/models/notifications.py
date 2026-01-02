"""Notification models for tracking push notification history and delivery status."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

metadata = MetaData()

notifications = Table(
    "notifications",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    ),
    Column("title", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("notification_type", String(50), nullable=False),
    Column("priority", String(20), nullable=False, server_default="normal"),
    Column("data", JSONB, nullable=True),
    Column("status", String(20), nullable=False, server_default="pending"),
    Column("sent_at", TIMESTAMP(timezone=True), nullable=True),
    Column("delivered_at", TIMESTAMP(timezone=True), nullable=True),
    Column("read_at", TIMESTAMP(timezone=True), nullable=True),
    Column("failure_reason", Text, nullable=True),
    Column("retry_count", Integer, nullable=False, server_default="0"),
    Column("max_retries", Integer, nullable=False, server_default="3"),
    Column("scheduled_for", TIMESTAMP(timezone=True), nullable=True),
    Column("expires_at", TIMESTAMP(timezone=True), nullable=True),
    Column("metadata", JSONB, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint(
        "notification_type IN ('appointment_reminder', 'appointment_confirmation', "
        "'appointment_cancelled', 'prescription_ready', 'pharmacy_update', "
        "'system_announcement', 'other')",
        name="notifications_type_check",
    ),
    CheckConstraint(
        "priority IN ('low', 'normal', 'high', 'urgent')",
        name="notifications_priority_check",
    ),
    CheckConstraint(
        "status IN ('pending', 'sent', 'delivered', 'failed', 'read')",
        name="notifications_status_check",
    ),
    Index("idx_notifications_user_id", "user_id"),
    Index("idx_notifications_status", "status"),
    Index("idx_notifications_created_at", "created_at", postgresql_ops={"created_at": "DESC"}),
    Index("idx_notifications_user_status", "user_id", "status"),
    Index("idx_notifications_type", "notification_type"),
    Index(
        "idx_notifications_scheduled",
        "scheduled_for",
        postgresql_where=text("scheduled_for IS NOT NULL"),
    ),
    Index(
        "idx_notifications_expires", "expires_at", postgresql_where=text("expires_at IS NOT NULL")
    ),
)

notification_deliveries = Table(
    "notification_deliveries",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "notification_id",
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "push_token_id",
        UUID(as_uuid=True),
        ForeignKey("push_tokens.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("fcm_message_id", Text, nullable=True),
    Column("delivery_status", String(20), nullable=False, server_default="pending"),
    Column("delivered_at", TIMESTAMP(timezone=True), nullable=True),
    Column("failure_reason", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint(
        "delivery_status IN ('pending', 'sent', 'delivered', 'failed', 'invalid_token')",
        name="notification_deliveries_status_check",
    ),
    UniqueConstraint("notification_id", "push_token_id", name="unique_notification_token"),
    Index("idx_notification_deliveries_notification", "notification_id"),
    Index("idx_notification_deliveries_token", "push_token_id"),
    Index("idx_notification_deliveries_status", "delivery_status"),
)
