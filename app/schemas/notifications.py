"""Push notification schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PushTokenRegister(BaseModel):
    """Schema for registering FCM token."""

    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    platform: str = Field(
        ...,
        description="Platform type",
        pattern="^(android|ios|web)$",
    )


class PushTokenResponse(BaseModel):
    """Schema for push token response."""

    id: UUID
    user_id: UUID
    fcm_token: str
    platform: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class SendNotificationRequest(BaseModel):
    """Schema for sending notification (admin only)."""

    user_id: UUID = Field(..., description="User ID to send notification to")
    title: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1, max_length=500)
    data: dict[str, str] | None = Field(default=None, description="Optional data payload")
    notification_type: Literal[
        "appointment_reminder",
        "appointment_confirmation",
        "appointment_cancelled",
        "prescription_ready",
        "pharmacy_update",
        "system_announcement",
        "other",
    ] = Field(default="other", description="Type of notification")
    priority: Literal["low", "normal", "high", "urgent"] = Field(
        default="normal", description="Notification priority"
    )


class NotificationResponse(BaseModel):
    """Schema for notification send response."""

    success_count: int
    failure_count: int
    message: str


class AdminNotificationRequest(BaseModel):
    """Schema for admin notification endpoint (secret key authenticated)."""

    user_id: UUID = Field(..., description="User ID to send notification to")
    title: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1, max_length=500)
    data: dict[str, str] | None = Field(default=None, description="Optional data payload")
    notification_type: Literal[
        "appointment_reminder",
        "appointment_confirmation",
        "appointment_cancelled",
        "prescription_ready",
        "pharmacy_update",
        "system_announcement",
        "other",
    ] = Field(default="other", description="Type of notification")
    priority: Literal["low", "normal", "high", "urgent"] = Field(
        default="normal", description="Notification priority"
    )


class NotificationRecord(BaseModel):
    """Schema for notification record."""

    id: UUID
    user_id: UUID
    title: str
    body: str
    notification_type: str
    priority: str
    data: dict | None
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failure_reason: str | None
    retry_count: int
    max_retries: int
    scheduled_for: datetime | None
    expires_at: datetime | None
    metadata: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class NotificationDeliveryRecord(BaseModel):
    """Schema for notification delivery record."""

    id: UUID
    notification_id: UUID
    push_token_id: UUID
    fcm_message_id: str | None
    delivery_status: str
    delivered_at: datetime | None
    failure_reason: str | None
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class NotificationHistoryResponse(BaseModel):
    """Schema for notification history response."""

    notifications: list[NotificationRecord]
    total: int
    page: int
    page_size: int


class NotificationDetailResponse(BaseModel):
    """Schema for detailed notification with delivery info."""

    notification: NotificationRecord
    deliveries: list[NotificationDeliveryRecord]
    total_devices: int
    successful_deliveries: int
    failed_deliveries: int
