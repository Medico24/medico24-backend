"""Appointment service for business logic."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.appointments import appointments
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentFilters,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)
from app.services.notification_service import NotificationService


class AppointmentService:
    """Service for managing appointments."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def create_appointment(
        self,
        patient_id: str,
        data: AppointmentCreate,
    ) -> AppointmentResponse:
        """
        Create a new appointment.

        Args:
            patient_id: ID of the patient creating the appointment
            data: Appointment creation data

        Returns:
            Created appointment
        """
        values = {
            "patient_id": UUID(patient_id),
            "doctor_id": data.doctor_id,
            "clinic_id": data.clinic_id,
            "doctor_name": data.doctor_name,
            "clinic_name": data.clinic_name,
            "appointment_at": data.appointment_at,
            "appointment_end_at": data.appointment_end_at,
            "reason": data.reason,
            "contact_phone": data.contact_phone,
            "notes": data.notes,
            "source": data.source.value,
            "status": AppointmentStatus.SCHEDULED.value,
        }

        stmt = insert(appointments).values(**values).returning(appointments)
        result = await self.db.execute(stmt)
        await self.db.commit()

        row = result.fetchone()
        appointment_response = AppointmentResponse.model_validate(dict(row._mapping))

        # Send push notification (async, non-blocking)
        try:
            await NotificationService.send_appointment_created_notification(
                db=self.db,
                user_id=patient_id,
                appointment_data=dict(row._mapping),
            )
        except Exception as e:
            # Log error but don't fail the request
            import structlog

            logger = structlog.get_logger()
            logger.warning("failed_to_send_appointment_notification", error=str(e))

        return appointment_response

    async def get_appointment(
        self,
        appointment_id: UUID,
        user_id: str,
    ) -> AppointmentResponse:
        """
        Get appointment by ID.

        Args:
            appointment_id: Appointment ID
            user_id: ID of requesting user

        Returns:
            Appointment details

        Raises:
            NotFoundException: If appointment not found
            ForbiddenException: If user doesn't have access
        """
        stmt = select(appointments).where(
            and_(
                appointments.c.id == appointment_id,
                appointments.c.deleted_at.is_(None),
            )
        )

        result = await self.db.execute(stmt)
        row = result.fetchone()

        if not row:
            raise NotFoundException("Appointment not found")

        # Check if user has access (is the patient)
        if str(row.patient_id) != user_id:
            raise ForbiddenException("Access denied to this appointment")

        return AppointmentResponse.model_validate(dict(row._mapping))

    async def list_appointments(
        self,
        user_id: str,
        filters: AppointmentFilters,
    ) -> AppointmentListResponse:
        """
        List appointments with filtering and pagination.

        Args:
            user_id: ID of requesting user
            filters: Filter and pagination parameters

        Returns:
            Paginated list of appointments
        """
        # Build where conditions
        conditions = [
            appointments.c.patient_id == UUID(user_id),
            appointments.c.deleted_at.is_(None),
        ]

        if filters.status:
            conditions.append(appointments.c.status == filters.status.value)

        if filters.doctor_id:
            conditions.append(appointments.c.doctor_id == filters.doctor_id)

        if filters.clinic_id:
            conditions.append(appointments.c.clinic_id == filters.clinic_id)

        if filters.from_date:
            conditions.append(appointments.c.appointment_at >= filters.from_date)

        if filters.to_date:
            conditions.append(appointments.c.appointment_at <= filters.to_date)

        # Count total
        count_stmt = select(func.count()).select_from(appointments).where(and_(*conditions))
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Get paginated results
        offset = (filters.page - 1) * filters.page_size

        stmt = (
            select(appointments)
            .where(and_(*conditions))
            .order_by(appointments.c.appointment_at.desc())
            .limit(filters.page_size)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        items = [AppointmentResponse.model_validate(dict(row._mapping)) for row in rows]

        return AppointmentListResponse(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            items=items,
        )

    async def update_appointment(
        self,
        appointment_id: UUID,
        user_id: str,
        data: AppointmentUpdate,
    ) -> AppointmentResponse:
        """
        Update an existing appointment.

        Args:
            appointment_id: Appointment ID
            user_id: ID of requesting user
            data: Update data

        Returns:
            Updated appointment

        Raises:
            NotFoundException: If appointment not found
            ForbiddenException: If user doesn't have access
        """
        # Check access
        await self.get_appointment(appointment_id, user_id)

        # Build update values
        update_values: dict[str, Any] = {}
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                if isinstance(value, AppointmentStatus):
                    update_values[field] = value.value
                else:
                    update_values[field] = value

        if not update_values:
            # No changes, return current state
            return await self.get_appointment(appointment_id, user_id)

        update_values["updated_at"] = datetime.utcnow()

        stmt = (
            update(appointments)
            .where(appointments.c.id == appointment_id)
            .values(**update_values)
            .returning(appointments)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        row = result.fetchone()
        return AppointmentResponse.model_validate(dict(row._mapping))

    async def update_appointment_status(
        self,
        appointment_id: UUID,
        user_id: str,
        data: AppointmentStatusUpdate,
    ) -> AppointmentResponse:
        """
        Update appointment status.

        Args:
            appointment_id: Appointment ID
            user_id: ID of requesting user
            data: Status update data

        Returns:
            Updated appointment
        """
        # Check access and get current state
        current_appointment = await self.get_appointment(appointment_id, user_id)
        old_status = current_appointment.status

        update_values = {
            "status": data.status.value,
            "updated_at": datetime.utcnow(),
        }

        if data.notes:
            update_values["notes"] = data.notes

        if data.status == AppointmentStatus.CANCELLED:
            update_values["cancelled_at"] = datetime.utcnow()

        stmt = (
            update(appointments)
            .where(appointments.c.id == appointment_id)
            .values(**update_values)
            .returning(appointments)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        row = result.fetchone()
        appointment_response = AppointmentResponse.model_validate(dict(row._mapping))

        # Send push notification if status changed (async, non-blocking)
        if old_status != data.status.value:
            try:
                await NotificationService.send_appointment_status_notification(
                    db=self.db,
                    user_id=user_id,
                    appointment_data=dict(row._mapping),
                    old_status=old_status,
                )
            except Exception as e:
                # Log error but don't fail the request
                import structlog

                logger = structlog.get_logger()
                logger.warning("failed_to_send_status_notification", error=str(e))

        return appointment_response

    async def delete_appointment(
        self,
        appointment_id: UUID,
        user_id: str,
        hard_delete: bool = False,
    ) -> None:
        """
        Delete an appointment (soft delete by default).

        Args:
            appointment_id: Appointment ID
            user_id: ID of requesting user
            hard_delete: If True, permanently delete the record

        Raises:
            NotFoundException: If appointment not found
            ForbiddenException: If user doesn't have access
        """
        # Check access
        await self.get_appointment(appointment_id, user_id)

        if hard_delete:
            stmt = delete(appointments).where(appointments.c.id == appointment_id)
        else:
            stmt = (
                update(appointments)  # type: ignore[assignment]
                .where(appointments.c.id == appointment_id)
                .values(
                    deleted_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )

        await self.db.execute(stmt)
        await self.db.commit()
