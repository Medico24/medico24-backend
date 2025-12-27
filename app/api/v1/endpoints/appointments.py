"""Appointment endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import CurrentUser, DatabaseSession
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentFilters,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)
from app.services.appointment_service import AppointmentService

router = APIRouter()


@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Appointments"],
    summary="Create new appointment",
)
async def create_appointment(
    data: AppointmentCreate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> AppointmentResponse:
    """
    Create a new appointment for the authenticated user.

    Args:
        data: Appointment creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Created appointment
    """
    service = AppointmentService(db)
    return await service.create_appointment(str(current_user["id"]), data)


@router.get(
    "/",
    response_model=AppointmentListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Appointments"],
    summary="List appointments",
)
async def list_appointments(
    current_user: CurrentUser,
    db: DatabaseSession,
    status_filter: AppointmentStatus | None = Query(None, alias="status"),
    doctor_id: UUID | None = Query(None),
    clinic_id: UUID | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AppointmentListResponse:
    """
    List appointments for the authenticated user with filtering.

    Args:
        current_user: Authenticated user
        db: Database session
        status_filter: Filter by status
        doctor_id: Filter by doctor ID
        clinic_id: Filter by clinic ID
        from_date: Filter by start date
        to_date: Filter by end date
        page: Page number
        page_size: Items per page

    Returns:
        Paginated list of appointments
    """
    from datetime import datetime

    filters = AppointmentFilters(
        status=status_filter,
        doctor_id=doctor_id,
        clinic_id=clinic_id,
        from_date=datetime.fromisoformat(from_date) if from_date else None,
        to_date=datetime.fromisoformat(to_date) if to_date else None,
        page=page,
        page_size=page_size,
    )

    service = AppointmentService(db)
    return await service.list_appointments(str(current_user["id"]), filters)


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Appointments"],
    summary="Get appointment by ID",
)
async def get_appointment(
    appointment_id: UUID,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> AppointmentResponse:
    """
    Get a specific appointment by ID.

    Args:
        appointment_id: Appointment ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Appointment details

    Raises:
        HTTPException: If appointment not found or access denied
    """
    service = AppointmentService(db)
    return await service.get_appointment(appointment_id, str(current_user["id"]))


@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Appointments"],
    summary="Update appointment",
)
async def update_appointment(
    appointment_id: UUID,
    data: AppointmentUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> AppointmentResponse:
    """
    Update an existing appointment.

    Args:
        appointment_id: Appointment ID
        data: Update data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated appointment

    Raises:
        HTTPException: If appointment not found or access denied
    """
    service = AppointmentService(db)
    return await service.update_appointment(appointment_id, str(current_user["id"]), data)


@router.patch(
    "/{appointment_id}/status",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Appointments"],
    summary="Update appointment status",
)
async def update_appointment_status(
    appointment_id: UUID,
    data: AppointmentStatusUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> AppointmentResponse:
    """
    Update appointment status (e.g., confirm, cancel, complete).

    Args:
        appointment_id: Appointment ID
        data: Status update data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated appointment

    Raises:
        HTTPException: If appointment not found or access denied
    """
    service = AppointmentService(db)
    return await service.update_appointment_status(appointment_id, str(current_user["id"]), data)


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Appointments"],
    summary="Delete appointment",
)
async def delete_appointment(
    appointment_id: UUID,
    current_user: CurrentUser,
    db: DatabaseSession,
    hard_delete: bool = Query(False),
) -> None:
    """
    Delete an appointment (soft delete by default).

    Args:
        appointment_id: Appointment ID
        current_user: Authenticated user
        db: Database session
        hard_delete: If true, permanently delete the record

    Raises:
        HTTPException: If appointment not found or access denied
    """
    service = AppointmentService(db)
    await service.delete_appointment(appointment_id, str(current_user["id"]), hard_delete)
