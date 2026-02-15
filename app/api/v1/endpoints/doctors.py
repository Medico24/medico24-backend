"""Doctor management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CacheManager
from app.database import get_db
from app.dependencies import get_cache_manager
from app.schemas.doctors import (
    DoctorCreate,
    DoctorDetailResponse,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
    DoctorVerificationRequest,
)
from app.services.doctor_service import DoctorService

router = APIRouter()


def get_doctor_service(cache_manager: CacheManager = Depends(get_cache_manager)) -> DoctorService:
    """Get doctor service instance."""
    return DoctorService(cache_manager=cache_manager)


# ============================================================================
# Doctor CRUD Endpoints
# ============================================================================


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    doctor_data: DoctorCreate,
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    Create a new doctor profile.

    - **user_id**: ID of the user account for this doctor
    - **license_number**: Medical license number (unique)
    - **specialization**: Primary medical specialization
    - **sub_specialization**: Sub-specialization if any
    - **qualification**: Medical qualifications
    - **experience_years**: Years of medical experience
    - **consultation_fee**: Default consultation fee
    - **consultation_duration_minutes**: Default consultation duration
    - **bio**: Doctor's biography
    - **languages_spoken**: List of languages the doctor speaks
    - **medical_council_registration**: Medical council registration number
    """
    try:
        doctor = await doctor_service.create_doctor(db, doctor_data)
        return doctor
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        if "doctors_license_number_key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Doctor with license number '{doctor_data.license_number}' already exists",
            ) from e
        if "doctors_email_key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Doctor with email '{doctor_data.email}' already exists",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create doctor"
        ) from e


@router.get("/", response_model=list[DoctorListResponse])
async def list_doctors(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    specialization: str | None = Query(None, description="Filter by specialization"),
    sub_specialization: str | None = Query(None, description="Filter by sub-specialization"),
    min_experience: int | None = Query(None, ge=0, description="Minimum years of experience"),
    max_experience: int | None = Query(None, ge=0, description="Maximum years of experience"),
    is_verified: bool | None = Query(None, description="Filter by verification status"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Minimum rating filter"),
    languages: list[str] | None = Query(None, description="Filter by spoken languages"),
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    List doctors with optional filtering.

    - **skip**: Pagination offset
    - **limit**: Number of results (max 100)
    - **specialization**: Filter by medical specialization
    - **sub_specialization**: Filter by sub-specialization
    - **min_experience/max_experience**: Filter by years of experience
    - **is_verified**: Filter verified doctors only
    - **min_rating**: Minimum rating threshold
    - **languages**: Filter by spoken languages
    """
    doctors_list = await doctor_service.get_doctors(
        db=db,
        skip=skip,
        limit=limit,
        specialization=specialization,
        sub_specialization=sub_specialization,
        min_experience=min_experience,
        max_experience=max_experience,
        is_verified=is_verified,
        min_rating=min_rating,
        languages=languages,
    )

    return [DoctorListResponse.model_validate(d) for d in doctors_list]


@router.get("/search", response_model=list[DoctorListResponse])
async def search_doctors(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    specialization: str | None = Query(None),
    sub_specialization: str | None = Query(None),
    min_experience: int | None = Query(None, ge=0),
    is_verified: bool | None = Query(None),
    min_rating: float | None = Query(None, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    Search doctors with advanced filtering.

    Supports filtering by:
    - Specialization and sub-specialization
    - Experience level
    - Verification status
    - Rating threshold
    """
    doctors_list = await doctor_service.get_doctors(
        db=db,
        skip=skip,
        limit=limit,
        specialization=specialization,
        sub_specialization=sub_specialization,
        min_experience=min_experience,
        is_verified=is_verified,
        min_rating=min_rating,
    )

    return [DoctorListResponse.model_validate(d) for d in doctors_list]


@router.get("/nearby", response_model=list[DoctorListResponse])
async def search_nearby_doctors(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=100),
    specialization: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_verified: bool = Query(True),
    min_rating: float | None = Query(None, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    Search for doctors near a specific location (through their clinic locations).

    - **latitude**: Location latitude
    - **longitude**: Location longitude
    - **radius_km**: Search radius in kilometers (default: 10km)
    - **specialization**: Filter by specialization
    - **is_verified**: Filter verified doctors only
    - **min_rating**: Minimum rating filter

    Returns doctors sorted by distance from the specified location.
    """
    doctors_list = await doctor_service.search_doctors_nearby(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        specialization=specialization,
        skip=skip,
        limit=limit,
        is_verified=is_verified,
        min_rating=min_rating,
    )

    return [DoctorListResponse.model_validate(d) for d in doctors_list]


@router.get("/{doctor_id}", response_model=DoctorDetailResponse)
async def get_doctor(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    Get doctor details by ID.

    Returns detailed information about a specific doctor including:
    - Professional credentials and qualifications
    - User information (name, contact)
    - Associated clinics with schedules and fees
    - Ratings and statistics
    """
    doctor = await doctor_service.get_doctor_with_details(db, doctor_id)

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    return doctor


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: UUID,
    doctor_data: DoctorUpdate,
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    Update doctor information.

    All fields are optional. Only provided fields will be updated.
    """
    try:
        doctor = await doctor_service.update_doctor(db, doctor_id, doctor_data)

        if not doctor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

        return doctor
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update doctor",
        ) from e


# ============================================================================
# Doctor Verification Endpoints
# ============================================================================


@router.post("/{doctor_id}/verify", response_model=DoctorResponse)
async def verify_doctor(
    doctor_id: UUID,
    verification_data: DoctorVerificationRequest,
    verified_by: UUID = Query(..., description="ID of admin verifying the doctor"),
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    Verify a doctor profile.

    This endpoint should be restricted to admins only.
    Marks the doctor as verified and records verification details.

    - **verified_by**: ID of the admin performing verification
    - **verification_documents**: Optional verification document metadata
    """
    doctor = await doctor_service.verify_doctor(
        db, doctor_id, verified_by, verification_data.verification_documents
    )

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    return doctor


@router.post("/{doctor_id}/unverify", response_model=DoctorResponse)
async def unverify_doctor(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor_service: DoctorService = Depends(get_doctor_service),
):
    """
    Remove verification from a doctor profile.

    This endpoint should be restricted to admins only.
    """
    doctor = await doctor_service.unverify_doctor(db, doctor_id)

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    return doctor
