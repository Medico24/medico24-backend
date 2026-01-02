"""Notification endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.notifications import (
    AdminNotificationRequest,
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
    )

    return NotificationResponse(
        success_count=success_count,
        failure_count=failure_count,
        message=f"Sent to {success_count} devices, {failure_count} failed",
    )
