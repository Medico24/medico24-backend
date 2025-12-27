"""Appointment schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AppointmentStatus(str, Enum):
    """Appointment status enumeration."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class AppointmentSource(str, Enum):
    """Appointment source enumeration."""

    PATIENT_APP = "patient_app"
    DOCTOR_APP = "doctor_app"
    ADMIN_PANEL = "admin_panel"
    API = "api"


class AppointmentBase(BaseModel):
    """Base appointment schema with common fields."""

    doctor_name: str = Field(..., min_length=1, max_length=200)
    clinic_name: str | None = Field(None, max_length=200)
    appointment_at: datetime
    appointment_end_at: datetime | None = None
    reason: str = Field(..., min_length=1, max_length=500)
    contact_phone: str = Field(..., min_length=7, max_length=20)
    notes: str | None = Field(None, max_length=1000)

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format."""
        # Remove common separators
        cleaned = (
            v.replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "")
        )
        if not cleaned.isdigit():
            raise ValueError("Phone number must contain only digits and separators")
        if len(cleaned) < 7:
            raise ValueError("Phone number must have at least 7 digits")
        return v

    @field_validator("appointment_end_at")
    @classmethod
    def validate_end_time(cls, v: datetime | None, info: any) -> datetime | None:
        """Validate end time is after start time."""
        if v and "appointment_at" in info.data:
            if v <= info.data["appointment_at"]:
                raise ValueError("End time must be after start time")
        return v


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment."""

    doctor_id: UUID | None = None
    clinic_id: UUID | None = None
    source: AppointmentSource = AppointmentSource.PATIENT_APP


class AppointmentUpdate(BaseModel):
    """Schema for updating an existing appointment."""

    doctor_name: str | None = Field(None, min_length=1, max_length=200)
    clinic_name: str | None = Field(None, max_length=200)
    doctor_id: UUID | None = None
    clinic_id: UUID | None = None
    appointment_at: datetime | None = None
    appointment_end_at: datetime | None = None
    reason: str | None = Field(None, min_length=1, max_length=500)
    contact_phone: str | None = Field(None, min_length=7, max_length=20)
    status: AppointmentStatus | None = None
    notes: str | None = Field(None, max_length=1000)


class AppointmentStatusUpdate(BaseModel):
    """Schema for updating appointment status."""

    status: AppointmentStatus
    notes: str | None = Field(None, max_length=1000)


class AppointmentResponse(AppointmentBase):
    """Schema for appointment response."""

    id: UUID
    patient_id: UUID
    doctor_id: UUID | None
    clinic_id: UUID | None
    status: AppointmentStatus
    source: str
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class AppointmentListResponse(BaseModel):
    """Schema for paginated appointment list response."""

    total: int
    page: int
    page_size: int
    items: list[AppointmentResponse]


class AppointmentFilters(BaseModel):
    """Schema for appointment filtering."""

    status: AppointmentStatus | None = None
    doctor_id: UUID | None = None
    clinic_id: UUID | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
