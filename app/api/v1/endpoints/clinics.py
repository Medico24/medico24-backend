"""Clinic management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CacheManager
from app.database import get_db
from app.dependencies import get_cache_manager
from app.schemas.clinics import (
    ClinicCreate,
    ClinicListResponse,
    ClinicResponse,
    ClinicUpdate,
)
from app.schemas.doctor_clinics import (
    ClinicForDoctorResponse,
    DoctorAtClinicResponse,
    DoctorClinicCreate,
    DoctorClinicResponse,
    DoctorClinicUpdate,
    EndAssociationRequest,
)
from app.services.clinic_service import ClinicService

router = APIRouter()


def get_clinic_service(cache_manager: CacheManager = Depends(get_cache_manager)) -> ClinicService:
    """Get clinic service instance."""
    return ClinicService(cache_manager=cache_manager)


# ============================================================================
# Clinic CRUD Endpoints
# ============================================================================


@router.post("/", response_model=ClinicResponse, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    clinic_data: ClinicCreate,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Create a new clinic.

    - **name**: Clinic name (required)
    - **slug**: URL-friendly identifier (auto-generated if not provided)
    - **description**: Clinic description
    - **logo_url**: URL to clinic logo
    - **contacts**: Contact information (phone, email, whatsapp, etc.)
    - **address**: Physical address
    - **latitude/longitude**: Geographic coordinates
    - **opening_hours**: Operating hours per day
    """
    try:
        clinic = await clinic_service.create_clinic(db, clinic_data)
        return clinic
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        if "clinics_slug_key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Clinic with slug '{clinic_data.slug}' already exists",
            ) from e
        if "clinics_status_check" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid clinic status"
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create clinic"
        ) from e


@router.get("/", response_model=list[ClinicListResponse])
async def list_clinics(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    is_active: bool = Query(True, description="Filter by active status"),
    status: str | None = Query(
        None, description="Filter by status (operational/under_maintenance/closed)"
    ),
    name_search: str | None = Query(None, description="Search clinics by name"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Minimum rating filter"),
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    List clinics with optional filtering.

    - **skip**: Pagination offset
    - **limit**: Number of results (max 100)
    - **is_active**: Filter active/inactive clinics
    - **status**: Filter by operational status
    - **name_search**: Search by clinic name
    - **min_rating**: Minimum rating threshold
    """
    clinics = await clinic_service.get_clinics(
        db=db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        status=status,
        name_search=name_search,
        min_rating=min_rating,
    )

    return [ClinicListResponse.model_validate(c) for c in clinics]


@router.get("/search", response_model=list[ClinicListResponse])
async def search_clinics(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool = Query(True),
    status: str | None = Query(None),
    name_search: str | None = Query(None),
    min_rating: float | None = Query(None, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Search clinics with advanced filtering.

    Supports filtering by:
    - Name search
    - Status
    - Minimum rating
    - Active status
    """
    clinics = await clinic_service.get_clinics(
        db=db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        status=status,
        name_search=name_search,
        min_rating=min_rating,
    )

    return [ClinicListResponse.model_validate(c) for c in clinics]


@router.get("/nearby", response_model=list[ClinicListResponse])
async def search_nearby_clinics(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool = Query(True),
    min_rating: float | None = Query(None, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Search for clinics near a specific location.

    - **latitude**: Location latitude
    - **longitude**: Location longitude
    - **radius_km**: Search radius in kilometers (default: 10km)
    - **is_active**: Filter active clinics only
    - **min_rating**: Minimum rating filter

    Returns clinics sorted by distance from the specified location.
    """
    clinics = await clinic_service.search_clinics_nearby(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        skip=skip,
        limit=limit,
        is_active=is_active,
        min_rating=min_rating,
    )

    return [ClinicListResponse.model_validate(c) for c in clinics]


@router.get("/{clinic_id}", response_model=ClinicResponse)
async def get_clinic(
    clinic_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Get clinic details by ID.

    Returns detailed information about a specific clinic.
    """
    clinic = await clinic_service.get_clinic_by_id(db, clinic_id)

    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    return clinic


@router.get("/slug/{slug}", response_model=ClinicResponse)
async def get_clinic_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Get clinic details by slug.

    Returns detailed information about a specific clinic by its URL-friendly slug.
    """
    clinic = await clinic_service.get_clinic_by_slug(db, slug)

    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    return clinic


@router.put("/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(
    clinic_id: UUID,
    clinic_data: ClinicUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Update clinic information.

    All fields are optional. Only provided fields will be updated.
    """
    try:
        clinic = await clinic_service.update_clinic(db, clinic_id, clinic_data)

        if not clinic:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

        return clinic
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        if "clinics_slug_key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Clinic with slug '{clinic_data.slug}' already exists",
            ) from e
        if "clinics_status_check" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid clinic status"
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update clinic"
        ) from e


@router.delete("/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinic(
    clinic_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Soft delete a clinic.

    The clinic will be marked as deleted but not removed from the database.
    """
    success = await clinic_service.soft_delete_clinic(db, clinic_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")


# ============================================================================
# Doctor-Clinic Association Endpoints
# ============================================================================


@router.post(
    "/{clinic_id}/doctors", response_model=DoctorClinicResponse, status_code=status.HTTP_201_CREATED
)
async def add_doctor_to_clinic(
    clinic_id: UUID,
    doctor_data: DoctorClinicCreate,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Add a doctor to a clinic.

    Creates an association between a doctor and a clinic with clinic-specific settings:
    - **doctor_id**: Doctor to add
    - **is_primary**: Whether this is the doctor's primary clinic
    - **consultation_fee**: Fee for this clinic (overrides doctor's default)
    - **consultation_duration_minutes**: Appointment duration
    - **department**: Department within the clinic
    - **designation**: Doctor's designation at this clinic
    - **available_days**: Days the doctor is available
    - **available_time_slots**: Available time slots per day
    - **appointment_booking_enabled**: Whether patients can book appointments
    """
    # Ensure the clinic_id matches
    if doctor_data.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinic ID in URL does not match request body",
        )

    try:
        association = await clinic_service.add_doctor_to_clinic(db, doctor_data)
        return association
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        if "doctor_clinics_doctor_id_clinic_id_unique_active" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor is already associated with this clinic",
            ) from e
        if "doctor_clinics_doctor_id_fkey" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
            ) from e
        if "doctor_clinics_clinic_id_fkey" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found"
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add doctor to clinic"
        ) from e


@router.get("/{clinic_id}/doctors", response_model=list[DoctorAtClinicResponse])
async def get_clinic_doctors(
    clinic_id: UUID,
    active_only: bool = Query(True, description="Filter active doctors only"),
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Get all doctors at a clinic.

    Returns a list of doctors working at the specified clinic with their
    clinic-specific information (fees, schedules, department, etc.).

    - **active_only**: If true, only returns currently active doctors
    """
    doctors = await clinic_service.get_clinic_doctors(db, clinic_id, active_only=active_only)
    return doctors


@router.get("/doctors/{doctor_id}/clinics", response_model=list[ClinicForDoctorResponse])
async def get_doctor_clinics(
    doctor_id: UUID,
    active_only: bool = Query(True, description="Filter active clinics only"),
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Get all clinics where a doctor works.

    Returns a list of clinics where the doctor has an association with
    clinic-specific information.

    - **active_only**: If true, only returns currently active associations
    """
    clinics = await clinic_service.get_doctor_clinics(db, doctor_id, active_only=active_only)
    return clinics


@router.put("/doctor-associations/{association_id}", response_model=DoctorClinicResponse)
async def update_doctor_clinic_association(
    association_id: UUID,
    update_data: DoctorClinicUpdate,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Update a doctor-clinic association.

    Allows updating clinic-specific settings for a doctor:
    - Consultation fee
    - Consultation duration
    - Department and designation
    - Available days and time slots
    - Appointment booking status
    """
    try:
        association = await clinic_service.update_doctor_clinic_association(
            db, association_id, update_data
        )

        if not association:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Doctor-clinic association not found"
            )

        return association
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update doctor-clinic association",
        ) from e


@router.post("/doctor-associations/{association_id}/end", response_model=DoctorClinicResponse)
async def end_doctor_clinic_association(
    association_id: UUID,
    request_data: EndAssociationRequest,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    End a doctor-clinic association.

    Marks the association as inactive with an end date.
    This is a soft delete - the association record is preserved for historical data.

    - **end_date**: Optional end date (defaults to current date/time)
    """
    association = await clinic_service.end_doctor_clinic_association(
        db, association_id, end_date=request_data.end_date
    )

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor-clinic association not found"
        )

    return association


@router.delete("/{clinic_id}/doctors/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_doctor_from_clinic(
    clinic_id: UUID,
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinic_service: ClinicService = Depends(get_clinic_service),
):
    """
    Remove a doctor from a clinic.

    Ends the active association between the doctor and clinic.
    This is a convenience endpoint equivalent to ending the association.
    """
    success = await clinic_service.remove_doctor_from_clinic(db, doctor_id, clinic_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active association found between this doctor and clinic",
        )
