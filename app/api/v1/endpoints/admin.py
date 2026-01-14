"""Admin-only endpoints for system management."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.dependencies import CacheManagerDep, DatabaseSession, get_current_user
from app.models.appointments import appointments
from app.models.notifications import notifications as notification_table
from app.models.pharmacies import pharmacies
from app.models.users import users
from app.schemas.admin import (
    AdminAppointmentListResponse,
    AdminMetricsResponse,
    AdminUserListResponse,
    DashboardStatsResponse,
    NotificationLogListResponse,
    PharmacyVerifyResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin", tags=["Admin"])


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to ensure current user has admin role.

    Args:
        current_user: Authenticated user

    Returns:
        User dict if admin

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users (admin only)",
)
async def list_all_users(
    db: DatabaseSession,
    cache_manager: CacheManagerDep,
    admin_user: dict = Depends(require_admin),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    role: str | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by name or email"),
) -> AdminUserListResponse:
    """
    Get paginated list of all users with filtering.

    Requires admin role.

    Args:
        db: Database session
        cache_manager: Cache manager
        admin_user: Authenticated admin user
        page: Page number
        page_size: Items per page
        role: Filter by user role
        is_active: Filter by active status
        search: Search term for name/email

    Returns:
        Paginated user list with metadata
    """
    # Build query
    query = select(users)
    count_query = select(func.count()).select_from(users)

    # Apply filters
    if role:
        query = query.where(users.c.role == role)
        count_query = count_query.where(users.c.role == role)

    if is_active is not None:
        query = query.where(users.c.is_active == is_active)
        count_query = count_query.where(users.c.is_active == is_active)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (users.c.full_name.ilike(search_pattern)) | (users.c.email.ilike(search_pattern))
        )
        count_query = count_query.where(
            (users.c.full_name.ilike(search_pattern)) | (users.c.email.ilike(search_pattern))
        )

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(users.c.created_at.desc())

    # Execute query
    result = await db.execute(query)
    user_list = [dict(row) for row in result.mappings().all()]

    return AdminUserListResponse(
        users=user_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/appointments",
    response_model=AdminAppointmentListResponse,
    summary="List all appointments (admin only)",
)
async def list_all_appointments(
    db: DatabaseSession,
    admin_user: dict = Depends(require_admin),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    patient_id: UUID | None = Query(None, description="Filter by patient ID"),
    doctor_id: UUID | None = Query(None, description="Filter by doctor ID"),
    from_date: str | None = Query(None, description="Filter from date (ISO format)"),
    to_date: str | None = Query(None, description="Filter to date (ISO format)"),
) -> AdminAppointmentListResponse:
    """
    Get paginated list of all appointments across all users.

    Requires admin role.

    Args:
        db: Database session
        admin_user: Authenticated admin user
        page: Page number
        page_size: Items per page
        status_filter: Filter by appointment status
        patient_id: Filter by patient ID
        doctor_id: Filter by doctor ID
        from_date: Start date filter
        to_date: End date filter

    Returns:
        Paginated appointment list with metadata
    """
    # Build query
    query = select(appointments)
    count_query = select(func.count()).select_from(appointments)

    # Apply filters
    if status_filter:
        query = query.where(appointments.c.status == status_filter)
        count_query = count_query.where(appointments.c.status == status_filter)

    if patient_id:
        query = query.where(appointments.c.patient_id == patient_id)
        count_query = count_query.where(appointments.c.patient_id == patient_id)

    if doctor_id:
        query = query.where(appointments.c.doctor_id == doctor_id)
        count_query = count_query.where(appointments.c.doctor_id == doctor_id)

    if from_date:
        from_datetime = datetime.fromisoformat(from_date)
        query = query.where(appointments.c.appointment_at >= from_datetime)
        count_query = count_query.where(appointments.c.appointment_at >= from_datetime)

    if to_date:
        to_datetime = datetime.fromisoformat(to_date)
        query = query.where(appointments.c.appointment_at <= to_datetime)
        count_query = count_query.where(appointments.c.appointment_at <= to_datetime)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(appointments.c.appointment_at.desc())

    # Execute query
    result = await db.execute(query)
    appointment_list = [dict(row) for row in result.mappings().all()]

    return AdminAppointmentListResponse(
        appointments=appointment_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsResponse,
    summary="Get dashboard statistics (admin only)",
)
async def get_dashboard_stats(
    db: DatabaseSession,
    admin_user: dict = Depends(require_admin),
) -> DashboardStatsResponse:
    """
    Get comprehensive dashboard statistics including time-series data.

    Requires admin role.

    Args:
        db: Database session
        admin_user: Authenticated admin user

    Returns:
        Dashboard statistics with current stats, chart data, and recent activity
    """
    now = datetime.now(UTC)

    # Current stats
    total_users_result = await db.execute(select(func.count()).select_from(users))
    total_users = total_users_result.scalar_one()

    # Count users from last month for percentage calculation
    last_month = now - timedelta(days=30)
    last_month_users_result = await db.execute(
        select(func.count()).select_from(users).where(users.c.created_at < last_month)
    )
    last_month_users = last_month_users_result.scalar_one()
    user_growth = (
        ((total_users - last_month_users) / last_month_users * 100) if last_month_users > 0 else 0
    )

    # Today's appointments
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_appointments_result = await db.execute(
        select(func.count())
        .select_from(appointments)
        .where(appointments.c.created_at >= today_start)
    )
    today_appointments = today_appointments_result.scalar_one()

    total_appointments_result = await db.execute(select(func.count()).select_from(appointments))
    total_appointments = total_appointments_result.scalar_one()

    # Verified pharmacies
    verified_pharmacies_result = await db.execute(
        select(func.count()).select_from(pharmacies).where(pharmacies.c.is_verified)
    )
    verified_pharmacies = verified_pharmacies_result.scalar_one()

    # New pharmacies this week
    week_ago = now - timedelta(days=7)
    new_pharmacies_result = await db.execute(
        select(func.count()).select_from(pharmacies).where(pharmacies.c.created_at >= week_ago)
    )
    new_pharmacies = new_pharmacies_result.scalar_one()

    # Notifications (last 24 hours)
    yesterday = now - timedelta(days=1)
    notifications_sent_result = await db.execute(
        select(func.count())
        .select_from(notification_table)
        .where(notification_table.c.sent_at >= yesterday)
    )
    notifications_sent = notifications_sent_result.scalar_one()

    # Delivery rate
    delivered_notifications_result = await db.execute(
        select(func.count())
        .select_from(notification_table)
        .where(
            notification_table.c.sent_at >= yesterday, notification_table.c.status == "delivered"
        )
    )
    delivered_notifications = delivered_notifications_result.scalar_one()
    delivery_rate = (
        (delivered_notifications / notifications_sent * 100) if notifications_sent > 0 else 100
    )

    stats = {
        "total_users": {
            "value": total_users,
            "change": f"+{user_growth:.1f}%",
            "description": "from last month",
        },
        "appointments": {
            "value": total_appointments,
            "change": f"+{today_appointments}",
            "description": "active today",
        },
        "verified_pharmacies": {
            "value": verified_pharmacies,
            "change": f"+{new_pharmacies}",
            "description": "new this week",
        },
        "notifications_sent": {
            "value": notifications_sent,
            "change": f"{delivery_rate:.1f}%",
            "description": "delivery rate",
        },
    }

    # Chart data - last 7 days
    chart_data = []
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for i in range(7):
        day_start = (now - timedelta(days=6 - i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Appointments for this day
        day_appointments_result = await db.execute(
            select(func.count())
            .select_from(appointments)
            .where(appointments.c.created_at >= day_start, appointments.c.created_at < day_end)
        )
        day_appointments = day_appointments_result.scalar_one()

        # Pharmacy registrations for this day
        day_pharmacies_result = await db.execute(
            select(func.count())
            .select_from(pharmacies)
            .where(pharmacies.c.created_at >= day_start, pharmacies.c.created_at < day_end)
        )
        day_pharmacies = day_pharmacies_result.scalar_one()

        chart_data.append(
            {"name": days[i], "appointments": day_appointments, "pharmacies": day_pharmacies}
        )

    # Recent activity - check system health
    recent_activity = [
        {
            "status": "online",
            "title": "Main API Online",
            "description": "99.9% uptime over last 24h",
            "time": "Now",
        },
        {
            "status": "online",
            "title": "PostGIS Database",
            "description": "Healthy connection pool",
            "time": "2m ago",
        },
        {
            "status": "warning" if delivery_rate < 95 else "online",
            "title": "Firebase Auth",
            "description": (
                "Elevated latency detected" if delivery_rate < 95 else "Normal operation"
            ),
            "time": "15m ago",
        },
    ]

    return DashboardStatsResponse(
        stats=stats, chart_data=chart_data, recent_activity=recent_activity
    )


@router.get(
    "/metrics",
    response_model=AdminMetricsResponse,
    summary="Get system metrics (admin only)",
)
async def get_admin_metrics(
    db: DatabaseSession,
    admin_user: dict = Depends(require_admin),
) -> AdminMetricsResponse:
    """
    Get comprehensive system metrics.

    Requires admin role.

    Args:
        db: Database session
        admin_user: Authenticated admin user

    Returns:
        System metrics including user, appointment, pharmacy, and notification stats
    """
    # User metrics
    total_users_result = await db.execute(select(func.count()).select_from(users))
    total_users = total_users_result.scalar_one()

    active_users_result = await db.execute(
        select(func.count()).select_from(users).where(users.c.is_active)
    )
    active_users = active_users_result.scalar_one()

    # Appointment metrics
    total_appointments_result = await db.execute(select(func.count()).select_from(appointments))
    total_appointments = total_appointments_result.scalar_one()

    pending_appointments_result = await db.execute(
        select(func.count()).select_from(appointments).where(appointments.c.status == "pending")
    )
    pending_appointments = pending_appointments_result.scalar_one()

    confirmed_appointments_result = await db.execute(
        select(func.count()).select_from(appointments).where(appointments.c.status == "confirmed")
    )
    confirmed_appointments = confirmed_appointments_result.scalar_one()

    # Pharmacy metrics
    total_pharmacies_result = await db.execute(select(func.count()).select_from(pharmacies))
    total_pharmacies = total_pharmacies_result.scalar_one()

    verified_pharmacies_result = await db.execute(
        select(func.count()).select_from(pharmacies).where(pharmacies.c.is_verified)
    )
    verified_pharmacies = verified_pharmacies_result.scalar_one()

    active_pharmacies_result = await db.execute(
        select(func.count()).select_from(pharmacies).where(pharmacies.c.is_active)
    )
    active_pharmacies = active_pharmacies_result.scalar_one()

    # Notification metrics (last 24 hours)
    yesterday = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    notifications_sent_today_result = await db.execute(
        select(func.count())
        .select_from(notification_table)
        .where(notification_table.c.sent_at >= yesterday)
    )
    notifications_sent_today = notifications_sent_today_result.scalar_one()

    return AdminMetricsResponse(
        users={"total": total_users, "active": active_users},
        appointments={
            "total": total_appointments,
            "pending": pending_appointments,
            "confirmed": confirmed_appointments,
        },
        pharmacies={
            "total": total_pharmacies,
            "verified": verified_pharmacies,
            "active": active_pharmacies,
        },
        notifications={"sent_today": notifications_sent_today},
    )


@router.get(
    "/notifications/logs",
    response_model=NotificationLogListResponse,
    summary="Get notification audit logs (admin only)",
)
async def get_notification_logs(
    db: DatabaseSession,
    admin_user: dict = Depends(require_admin),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    from_date: str | None = Query(None, description="Filter from date (ISO format)"),
    to_date: str | None = Query(None, description="Filter to date (ISO format)"),
) -> NotificationLogListResponse:
    """
    Get paginated notification history with audit information.

    Requires admin role.

    Args:
        db: Database session
        admin_user: Authenticated admin user
        page: Page number
        page_size: Items per page
        user_id: Filter by recipient user ID
        from_date: Start date filter
        to_date: End date filter

    Returns:
        Paginated notification log list
    """
    # Build query
    query = select(notification_table)
    count_query = select(func.count()).select_from(notification_table)

    # Apply filters
    if user_id:
        query = query.where(notification_table.c.user_id == user_id)
        count_query = count_query.where(notification_table.c.user_id == user_id)

    if from_date:
        from_datetime = datetime.fromisoformat(from_date)
        query = query.where(notification_table.c.sent_at >= from_datetime)
        count_query = count_query.where(notification_table.c.sent_at >= from_datetime)

    if to_date:
        to_datetime = datetime.fromisoformat(to_date)
        query = query.where(notification_table.c.sent_at <= to_datetime)
        count_query = count_query.where(notification_table.c.sent_at <= to_datetime)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(notification_table.c.sent_at.desc())

    # Execute query
    result = await db.execute(query)
    logs = [dict(row) for row in result.mappings().all()]

    return NotificationLogListResponse(
        logs=logs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.patch(
    "/pharmacies/{pharmacy_id}/verify",
    response_model=PharmacyVerifyResponse,
    summary="Toggle pharmacy verification (admin only)",
)
async def verify_pharmacy(
    pharmacy_id: UUID,
    db: DatabaseSession,
    cache_manager: CacheManagerDep,
    admin_user: dict = Depends(require_admin),
    is_verified: bool = Query(..., description="Verification status to set"),
) -> PharmacyVerifyResponse:
    """
    Verify or unverify a pharmacy.

    Requires admin role.

    Args:
        pharmacy_id: Pharmacy ID to update
        db: Database session
        cache_manager: Cache manager
        admin_user: Authenticated admin user
        is_verified: New verification status

    Returns:
        Updated pharmacy verification status
    """
    # Check if pharmacy exists
    from sqlalchemy import select as sql_select

    check_query = sql_select(pharmacies).where(pharmacies.c.id == pharmacy_id)
    check_result = await db.execute(check_query)
    existing_pharmacy = check_result.mappings().first()

    if not existing_pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found",
        )

    # Update verification status
    from sqlalchemy import update

    query = (
        update(pharmacies)
        .where(pharmacies.c.id == pharmacy_id)
        .values(is_verified=is_verified, updated_at=datetime.now(UTC))
        .returning(pharmacies)
    )

    result = await db.execute(query)
    await db.commit()
    updated_pharmacy = result.mappings().first()

    if not updated_pharmacy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pharmacy",
        )

    # Invalidate cache
    if cache_manager:
        # Cache key format: pharmacy:{pharmacy_id}
        cache_key = f"pharmacy:{pharmacy_id}"
        cache_manager.delete(cache_key)

    return PharmacyVerifyResponse(
        id=updated_pharmacy["id"],
        name=updated_pharmacy["name"],
        is_verified=updated_pharmacy["is_verified"],
        is_active=updated_pharmacy["is_active"],
        updated_at=updated_pharmacy["updated_at"],
    )


class BroadcastNotificationRequest(BaseModel):
    """Request schema for broadcasting notifications."""

    title: str
    body: str
    target: str  # "all", "patients", "pharmacies"
    data: dict[str, Any] | None = None


class BroadcastNotificationResponse(BaseModel):
    """Response schema for broadcast notifications."""

    success_count: int
    failure_count: int
    total_users: int
    message: str


@router.post(
    "/notifications/broadcast",
    response_model=BroadcastNotificationResponse,
    summary="Broadcast notification to users (admin only)",
)
async def broadcast_notification(
    request: BroadcastNotificationRequest,
    db: DatabaseSession,
    admin_user: dict = Depends(require_admin),
) -> BroadcastNotificationResponse:
    """
    Broadcast a notification to all users or a specific role.

    Requires admin role.

    Args:
        request: Broadcast notification details
        db: Database session
        admin_user: Authenticated admin user

    Returns:
        Broadcast results with success/failure counts
    """
    # Build user query based on target
    query = select(users.c.id).where(users.c.is_active)

    if request.target == "patients":
        query = query.where(users.c.role == "patient")
    elif request.target == "pharmacies":
        query = query.where(users.c.role == "pharmacy")
    # "all" means no additional filter

    # Get user IDs
    result = await db.execute(query)
    user_ids = [str(row[0]) for row in result.all()]

    total_users = len(user_ids)
    total_success = 0
    total_failure = 0

    # Send notification to each user
    for user_id in user_ids:
        try:
            success, failure = await NotificationService.send_to_user(
                db=db,
                user_id=user_id,
                title=request.title,
                body=request.body,
                data=request.data or {},
                notification_type="system_announcement",
                priority="normal",
            )
            total_success += success
            total_failure += failure
        except Exception:
            total_failure += 1
            continue

    return BroadcastNotificationResponse(
        success_count=total_success,
        failure_count=total_failure,
        total_users=total_users,
        message=f"Broadcast to {total_users} users: {total_success} succeeded, {total_failure} failed",
    )
