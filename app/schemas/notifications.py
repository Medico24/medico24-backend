"""Push notification schemas."""

from datetime import datetime
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


class NotificationResponse(BaseModel):
    """Schema for notification send response."""

    success_count: int
    failure_count: int
    message: str
    message: str
