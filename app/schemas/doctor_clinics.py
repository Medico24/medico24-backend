"""Doctor-Clinic association schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

# ============================================================================
# Doctor-Clinic Association Schemas
# ============================================================================


class DoctorClinicBase(BaseModel):
    """Base schema for doctor-clinic association."""

    is_primary: bool = False
    consultation_fee: Decimal | None = Field(
        None, ge=0, description="Clinic-specific consultation fee"
    )
    consultation_duration_minutes: int | None = Field(None, ge=5, le=180)
    department: str | None = Field(None, max_length=200)
    designation: str | None = Field(
        None,
        max_length=200,
        description="e.g., Consultant, Senior Consultant, HOD, Visiting Doctor",
    )
    available_days: list[str] | None = Field(
        None, description='List of available days: ["monday", "wednesday", "friday"]'
    )
    available_time_slots: list[dict] | None = Field(
        None,
        description='Time slots: [{"day": "monday", "slots": [{"start": "09:00", "end": "13:00"}]}]',
    )
    appointment_booking_enabled: bool = True


class DoctorClinicCreate(DoctorClinicBase):
    """Schema for creating a doctor-clinic association."""

    doctor_id: UUID
    clinic_id: UUID


class DoctorClinicUpdate(BaseModel):
    """Schema for updating a doctor-clinic association."""

    is_primary: bool | None = None
    consultation_fee: Decimal | None = Field(None, ge=0)
    consultation_duration_minutes: int | None = Field(None, ge=5, le=180)
    department: str | None = None
    designation: str | None = None
    available_days: list[str] | None = None
    available_time_slots: list[dict] | None = None
    appointment_booking_enabled: bool | None = None
    status: str | None = Field(None, pattern="^(active|on_leave|temporarily_unavailable|inactive)$")


class DoctorClinicResponse(DoctorClinicBase):
    """Doctor-clinic association response schema."""

    id: UUID
    doctor_id: UUID
    clinic_id: UUID
    start_date: datetime
    end_date: datetime | None = None
    total_appointments: int = 0
    completed_appointments: int = 0
    rating_at_clinic: Decimal | None = None
    rating_count_at_clinic: int = 0
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("consultation_fee", "rating_at_clinic", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class DoctorAtClinicResponse(BaseModel):
    """Doctor information at a specific clinic."""

    doctor_id: UUID
    doctor_name: str
    specialization: str | None
    license_number: str | None
    experience_years: int | None
    consultation_fee: Decimal | None
    consultation_duration_minutes: int | None
    department: str | None
    designation: str | None
    available_days: list[str] | None
    available_time_slots: list[dict] | None
    rating_at_clinic: Decimal | None
    rating_count_at_clinic: int
    is_primary: bool
    status: str

    model_config = {"from_attributes": True}

    @field_serializer("consultation_fee", "rating_at_clinic", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class ClinicForDoctorResponse(BaseModel):
    """Clinic information for a specific doctor."""

    clinic_id: UUID
    clinic_name: str
    clinic_address: str
    clinic_latitude: Decimal | None
    clinic_longitude: Decimal | None
    consultation_fee: Decimal | None
    department: str | None
    designation: str | None
    available_days: list[str] | None
    is_primary: bool
    status: str

    model_config = {"from_attributes": True}

    @field_serializer("clinic_latitude", "clinic_longitude", "consultation_fee", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class EndAssociationRequest(BaseModel):
    """Request to end a doctor-clinic association."""

    end_date: datetime | None = Field(
        None, description="End date for the association. Defaults to current time if not provided."
    )
