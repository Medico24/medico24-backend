"""Admin-specific schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminUserListResponse(BaseModel):
    """Response schema for admin user listing."""

    users: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class AdminAppointmentListResponse(BaseModel):
    """Response schema for admin appointment listing."""

    appointments: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class AdminMetricsResponse(BaseModel):
    """Response schema for admin metrics."""

    users: dict[str, int] = Field(
        ..., description="User metrics (total, active)", example={"total": 1000, "active": 850}
    )
    appointments: dict[str, int] = Field(
        ...,
        description="Appointment metrics (total, pending, confirmed)",
        example={"total": 5000, "pending": 120, "confirmed": 200},
    )
    pharmacies: dict[str, int] = Field(
        ...,
        description="Pharmacy metrics (total, verified, active)",
        example={"total": 150, "verified": 120, "active": 145},
    )
    notifications: dict[str, int] = Field(
        ..., description="Notification metrics (sent_today)", example={"sent_today": 320}
    )

    model_config = ConfigDict(from_attributes=True)


class NotificationLogListResponse(BaseModel):
    """Response schema for notification logs."""

    logs: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class PharmacyVerifyResponse(BaseModel):
    """Response schema for pharmacy verification."""

    id: UUID
    name: str
    is_verified: bool
    is_active: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
