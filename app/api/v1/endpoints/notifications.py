"""Notification endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.notifications import (
    AdminNotificationRequest,
    NotificationDetailResponse,
    NotificationHistoryResponse,
    NotificationRecord,
    NotificationResponse,
    PushTokenRegister,
    PushTokenResponse,
    SendNotificationRequest,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/register-token",
    response_model=PushTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register FCM token",
)
async def register_fcm_token(
    token_data: PushTokenRegister,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushTokenResponse:
    """
    Register or update FCM token for the authenticated user.

    This endpoint should be called:
    - After successful login
    - When FCM token is refreshed
    - When user switches devices

    Args:
        token_data: FCM token and platform information
        current_user: Authenticated user
        db: Database session

    Returns:
        Registered token details
    """
    try:
        token = await NotificationService.register_token(
            db=db,
            user_id=str(current_user["id"]),
            fcm_token=token_data.fcm_token,
            platform=token_data.platform,
        )

        return PushTokenResponse.model_validate(token)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to register token: {e!s}",
        )


@router.delete(
    "/deactivate-token",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate FCM token",
)
async def deactivate_fcm_token(
    token_data: PushTokenRegister,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deactivate a specific FCM token.

    This should be called when:
    - User logs out on a specific device
    - User uninstalls the app
    - Token becomes invalid

    Args:
        token_data: FCM token to deactivate
        current_user: Authenticated user
        db: Database session
    """
    await NotificationService.deactivate_token(
        db=db,
        user_id=str(current_user["id"]),
        fcm_token=token_data.fcm_token,
    )


@router.delete(
    "/deactivate-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate all user tokens",
)
async def deactivate_all_tokens(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deactivate all FCM tokens for the current user.

    This should be called when:
    - User logs out from all devices
    - User deletes their account

    Args:
        current_user: Authenticated user
        db: Database session
    """
    await NotificationService.deactivate_all_user_tokens(
        db=db,
        user_id=str(current_user["id"]),
    )


@router.post(
    "/send",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Send notification to user (admin only)",
)
async def send_notification(
    request: SendNotificationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """
    Send a push notification to a specific user.

    This is an admin endpoint for manual notifications.

    Args:
        request: Notification details
        current_user: Authenticated user (must be admin)
        db: Database session

    Returns:
        Number of successful and failed sends

    Raises:
        HTTPException: If user is not admin
    """
    # Check if user is admin
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can send notifications",
        )

    success_count, failure_count = await NotificationService.send_to_user(
        db=db,
        user_id=str(request.user_id),
        title=request.title,
        body=request.body,
        data=request.data,
        notification_type=request.notification_type,
        priority=request.priority,
    )

    return NotificationResponse(
        success_count=success_count,
        failure_count=failure_count,
        message=f"Sent to {success_count} devices, {failure_count} failed",
    )


@router.post(
    "/admin-send",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Send notification using admin secret key",
)
async def admin_send_notification(
    request: AdminNotificationRequest,
    db: AsyncSession = Depends(get_db),
    x_admin_secret: str = Header(..., description="Admin secret key"),
) -> NotificationResponse:
    """
    Send a push notification to a specific user using admin secret key.

    This endpoint bypasses normal authentication and uses a secret key instead.
    Use this for external systems or scripts that need to send notifications.

    Args:
        request: Notification details including user_id
        db: Database session
        x_admin_secret: Admin secret key (from X-Admin-Secret header)

    Returns:
        Number of successful and failed sends

    Raises:
        HTTPException: If secret key is invalid
    """
    # Verify admin secret key
    if x_admin_secret != settings.admin_notification_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin secret key",
        )

    success_count, failure_count = await NotificationService.send_to_user(
        db=db,
        user_id=str(request.user_id),
        title=request.title,
        body=request.body,
        data=request.data,
        notification_type=request.notification_type,
        priority=request.priority,
    )

    return NotificationResponse(
        success_count=success_count,
        failure_count=failure_count,
        message=f"Sent to {success_count} devices, {failure_count} failed",
    )


@router.get(
    "/history",
    response_model=NotificationHistoryResponse,
    summary="Get current user's notification history",
)
async def get_my_notification_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    notification_type: str | None = Query(None, description="Filter by type"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationHistoryResponse:
    """
    Get notification history for the authenticated user.

    Args:
        page: Page number (starts at 1)
        page_size: Number of items per page (max 100)
        status: Optional status filter
        notification_type: Optional type filter
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated notification history
    """
    result = await NotificationService.get_user_notifications(
        db=db,
        user_id=str(current_user["id"]),
        page=page,
        page_size=page_size,
        status_filter=status,
        notification_type_filter=notification_type,
    )

    return NotificationHistoryResponse(
        notifications=[NotificationRecord.model_validate(n) for n in result["notifications"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/history/{user_id}",
    response_model=NotificationHistoryResponse,
    summary="Get user notification history (admin only)",
)
async def get_user_notification_history(
    user_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    notification_type: str | None = Query(None, description="Filter by type"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationHistoryResponse:
    """
    Get notification history for a specific user (admin only).

    Args:
        user_id: Target user ID
        page: Page number (starts at 1)
        page_size: Number of items per page (max 100)
        status: Optional status filter
        notification_type: Optional type filter
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Paginated notification history

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view other users' notifications",
        )

    result = await NotificationService.get_user_notifications(
        db=db,
        user_id=str(user_id),
        page=page,
        page_size=page_size,
        status_filter=status,
        notification_type_filter=notification_type,
    )

    return NotificationHistoryResponse(
        notifications=[NotificationRecord.model_validate(n) for n in result["notifications"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationDetailResponse,
    summary="Get notification details",
)
async def get_notification_detail(
    notification_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationDetailResponse:
    """
    Get detailed notification information including delivery status.

    Args:
        notification_id: Notification ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Notification details with delivery information

    Raises:
        HTTPException: If notification not found or access denied
    """
    # Admins can view any notification, users can only view their own
    user_id_filter = None if current_user.get("role") == "admin" else str(current_user["id"])

    result = await NotificationService.get_notification_by_id(
        db=db,
        notification_id=str(notification_id),
        user_id=user_id_filter,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return NotificationDetailResponse(
        notification=NotificationRecord.model_validate(result["notification"]),
        deliveries=result["deliveries"],
        total_devices=result["total_devices"],
        successful_deliveries=result["successful_deliveries"],
        failed_deliveries=result["failed_deliveries"],
    )


@router.patch(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark notification as read",
)
async def mark_notification_read(
    notification_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Mark a notification as read.

    Args:
        notification_id: Notification ID
        current_user: Authenticated user
        db: Database session

    Raises:
        HTTPException: If notification not found
    """
    success = await NotificationService.mark_notification_as_read(
        db=db,
        notification_id=str(notification_id),
        user_id=str(current_user["id"]),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
)
async def delete_notification(
    notification_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a notification.

    Users can delete their own notifications.
    Admins can delete any notification.

    Args:
        notification_id: Notification ID
        current_user: Authenticated user
        db: Database session

    Raises:
        HTTPException: If notification not found
    """
    # Admins can delete any notification, users can only delete their own
    user_id_filter = None if current_user.get("role") == "admin" else str(current_user["id"])

    success = await NotificationService.delete_notification(
        db=db,
        notification_id=str(notification_id),
        user_id=user_id_filter,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.get(
    "/stats/summary",
    summary="Get notification statistics",
)
async def get_notification_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get notification statistics for the authenticated user.

    Admins get global stats, users get their own stats.

    Args:
        days: Number of days to look back (max 365)
        current_user: Authenticated user
        db: Database session

    Returns:
        Statistics summary
    """
    # Admins get global stats, users get their own
    user_id_filter = None if current_user.get("role") == "admin" else str(current_user["id"])

    stats = await NotificationService.get_notification_stats(
        db=db,
        user_id=user_id_filter,
        days=days,
    )

    return stats
