"""Doctor schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

# ============================================================================
# Doctor Base Schemas
# ============================================================================


class DoctorBase(BaseModel):
    """Base schema for doctor."""

    email: str
    full_name: str
    phone: str | None = None
    profile_picture_url: str | None = None
    license_number: str = Field(..., min_length=1, max_length=100)
    specialization: str = Field(..., min_length=1, max_length=200)
    sub_specialization: str | None = Field(None, max_length=200)
    qualification: str | None = None
    experience_years: int | None = Field(None, ge=0)
    consultation_fee: Decimal | None = Field(None, ge=0, decimal_places=2)
    consultation_duration_minutes: int | None = Field(None, ge=15, le=180)
    bio: str | None = None
    languages_spoken: list[str] | None = None
    medical_council_registration: str | None = Field(None, max_length=100)


class DoctorCreate(DoctorBase):
    """Schema for creating a doctor."""


class DoctorUpdate(BaseModel):
    """Schema for updating a doctor."""

    specialization: str | None = Field(None, min_length=1, max_length=200)
    sub_specialization: str | None = None
    qualification: str | None = None
    experience_years: int | None = Field(None, ge=0)
    consultation_fee: Decimal | None = Field(None, ge=0, decimal_places=2)
    consultation_duration_minutes: int | None = Field(None, ge=15, le=180)
    bio: str | None = None
    languages_spoken: list[str] | None = None
    medical_council_registration: str | None = None


class DoctorResponse(DoctorBase):
    """Doctor response schema."""

    id: UUID
    is_verified: bool
    verification_documents: dict | None = None
    verified_at: datetime | None = None
    verified_by: UUID | None = None
    rating: Decimal | None = None
    rating_count: int = 0
    total_patients_treated: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("consultation_fee", "rating", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class DoctorListResponse(BaseModel):
    """Doctor schema for list responses."""

    id: UUID
    email: str
    full_name: str
    phone: str | None
    profile_picture_url: str | None
    license_number: str
    specialization: str
    sub_specialization: str | None
    experience_years: int | None
    consultation_fee: Decimal | None
    is_verified: bool
    rating: Decimal | None
    rating_count: int

    model_config = {"from_attributes": True}

    @field_serializer("consultation_fee", "rating", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class DoctorDetailResponse(DoctorResponse):
    """Detailed doctor response with user info and clinics."""

    # Clinic associations
    clinics: list[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ============================================================================
# Doctor Verification Schemas
# ============================================================================


class DoctorVerificationRequest(BaseModel):
    """Schema for verifying a doctor."""

    verification_documents: dict | None = None
    notes: str | None = None


class DoctorVerificationResponse(BaseModel):
    """Doctor verification response."""

    id: UUID
    is_verified: bool
    verified_at: datetime | None
    verified_by: UUID | None

    model_config = {"from_attributes": True}


# ============================================================================
# Doctor Search Schemas
# ============================================================================


class DoctorSearchParams(BaseModel):
    """Doctor search parameters."""

    specialization: str | None = None
    sub_specialization: str | None = None
    min_experience: int | None = Field(None, ge=0)
    max_experience: int | None = Field(None, ge=0)
    is_verified: bool | None = None
    min_rating: Decimal | None = Field(None, ge=0, le=5)
    languages: list[str] | None = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


class DoctorNearbySearch(BaseModel):
    """Schema for nearby doctor search (through clinics)."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(10.0, gt=0, le=100)
    specialization: str | None = None
    is_verified: bool = True
    min_rating: Decimal | None = Field(None, ge=0, le=5)
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
