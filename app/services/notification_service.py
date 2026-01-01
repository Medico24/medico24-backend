"""Notification service for sending push notifications via FCM."""

from datetime import UTC
from typing import Any

import structlog
from firebase_admin import messaging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_tokens import push_tokens

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for managing push notifications."""

    @staticmethod
    async def send_push_notification(
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> tuple[int, int]:
        """
        Send push notification to multiple devices.

        Args:
            tokens: List of FCM tokens
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Tuple of (success_count, failure_count)
        """
        if not tokens:
            logger.warning("no_tokens_provided", title=title)
            return 0, 0

        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=tokens,
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        ),
                    ),
                ),
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        priority="high",
                    ),
                ),
            )

            response = messaging.send_each_for_multicast(message)

            logger.info(
                "push_notification_sent",
                title=title,
                success_count=response.success_count,
                failure_count=response.failure_count,
            )

            return response.success_count, response.failure_count

        except Exception as e:
            logger.error("push_notification_failed", error=str(e), title=title)
            return 0, len(tokens)

    @staticmethod
    async def send_to_user(
        db: AsyncSession,
        user_id: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> tuple[int, int]:
        """
        Send notification to all active devices of a user.

        Args:
            db: Database session
            user_id: User ID
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Tuple of (success_count, failure_count)
        """
        # Get all active tokens for user
        query = select(push_tokens.c.fcm_token).where(
            push_tokens.c.user_id == user_id,
            push_tokens.c.is_active == True,  # noqa: E712
        )

        result = await db.execute(query)
        tokens = [row[0] for row in result.fetchall()]

        if not tokens:
            logger.warning("no_active_tokens_for_user", user_id=user_id)
            return 0, 0

        return await NotificationService.send_push_notification(
            tokens=tokens,
            title=title,
            body=body,
            data=data,
        )

    @staticmethod
    async def register_token(
        db: AsyncSession,
        user_id: str,
        fcm_token: str,
        platform: str,
    ) -> dict[str, Any]:
        """
        Register or update FCM token for a user.

        Args:
            db: Database session
            user_id: User ID
            fcm_token: FCM token
            platform: Platform (android, ios, web)

        Returns:
            Created/updated token record
        """
        from datetime import datetime

        # Deactivate old tokens for this user on the same platform
        await db.execute(
            update(push_tokens)
            .where(
                push_tokens.c.user_id == user_id,
                push_tokens.c.platform == platform,
                push_tokens.c.fcm_token != fcm_token,
            )
            .values(is_active=False)
        )

        # Check if token already exists
        query = select(push_tokens).where(
            push_tokens.c.user_id == user_id,
            push_tokens.c.fcm_token == fcm_token,
        )
        result = await db.execute(query)
        existing_token = result.first()

        if existing_token:
            # Update existing token
            await db.execute(
                update(push_tokens)
                .where(push_tokens.c.id == existing_token.id)
                .values(
                    is_active=True,
                    last_used_at=datetime.now(UTC),
                    platform=platform,
                )
            )
            await db.commit()

            # Fetch updated record
            result = await db.execute(
                select(push_tokens).where(push_tokens.c.id == existing_token.id)
            )
            return dict(result.first()._mapping)

        # Insert new token
        insert_stmt = push_tokens.insert().values(
            user_id=user_id,
            fcm_token=fcm_token,
            platform=platform,
            is_active=True,
            last_used_at=datetime.now(UTC),
        )
        result = await db.execute(insert_stmt)
        await db.commit()

        # Fetch created record
        new_id = result.inserted_primary_key[0]
        result = await db.execute(select(push_tokens).where(push_tokens.c.id == new_id))
        return dict(result.first()._mapping)

    @staticmethod
    async def deactivate_token(
        db: AsyncSession,
        user_id: str,
        fcm_token: str,
    ) -> bool:
        """
        Deactivate a specific FCM token.

        Args:
            db: Database session
            user_id: User ID
            fcm_token: FCM token to deactivate

        Returns:
            True if token was deactivated
        """
        result = await db.execute(
            update(push_tokens)
            .where(
                push_tokens.c.user_id == user_id,
                push_tokens.c.fcm_token == fcm_token,
            )
            .values(is_active=False)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def deactivate_all_user_tokens(
        db: AsyncSession,
        user_id: str,
    ) -> int:
        """
        Deactivate all tokens for a user (logout).

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of tokens deactivated
        """
        result = await db.execute(
            update(push_tokens).where(push_tokens.c.user_id == user_id).values(is_active=False)
        )
        await db.commit()
        return result.rowcount

    @staticmethod
    async def send_appointment_created_notification(
        db: AsyncSession,
        user_id: str,
        appointment_data: dict[str, Any],
    ) -> None:
        """
        Send notification when appointment is created.

        Args:
            db: Database session
            user_id: Patient user ID
            appointment_data: Appointment details
        """
        from datetime import datetime

        appointment_time = appointment_data.get("appointment_at")
        if isinstance(appointment_time, datetime):
            appointment_time_str = appointment_time.strftime("%b %d, %I:%M %p")
        else:
            appointment_time_str = str(appointment_time)

        await NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            title="Appointment Scheduled",
            body=f"Appointment with {appointment_data.get('doctor_name')} on {appointment_time_str}",
            data={
                "type": "appointment_created",
                "appointment_id": str(appointment_data.get("id")),
                "screen": "/appointments",
            },
        )

    @staticmethod
    async def send_appointment_status_notification(
        db: AsyncSession,
        user_id: str,
        appointment_data: dict[str, Any],
        old_status: str,
    ) -> None:
        """
        Send notification when appointment status changes.

        Args:
            db: Database session
            user_id: Patient user ID
            appointment_data: Appointment details
            old_status: Previous status
        """
        new_status = appointment_data.get("status")
        doctor_name = appointment_data.get("doctor_name")

        status_messages = {
            "confirmed": f"Your appointment with {doctor_name} has been confirmed",
            "cancelled": f"Your appointment with {doctor_name} has been cancelled",
            "rescheduled": f"Your appointment with {doctor_name} has been rescheduled",
            "completed": f"Your appointment with {doctor_name} is completed",
        }

        body = status_messages.get(
            new_status,
            f"Appointment status updated to {new_status}",
        )

        await NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            title="Appointment Update",
            body=body,
            data={
                "type": "appointment_status_changed",
                "appointment_id": str(appointment_data.get("id")),
                "old_status": old_status,
                "new_status": new_status,
                "screen": f"/appointments/{appointment_data.get('id')}",
            },
        )

    @staticmethod
    async def send_appointment_reminder(
        db: AsyncSession,
        user_id: str,
        appointment_data: dict[str, Any],
        hours_before: int,
    ) -> None:
        """
        Send appointment reminder notification.

        Args:
            db: Database session
            user_id: Patient user ID
            appointment_data: Appointment details
            hours_before: Hours before appointment (24 or 1)
        """
        from datetime import datetime

        appointment_time = appointment_data.get("appointment_at")
        if isinstance(appointment_time, datetime):
            appointment_time_str = appointment_time.strftime("%b %d at %I:%M %p")
        else:
            appointment_time_str = str(appointment_time)

        if hours_before == 24:
            title = "Appointment Tomorrow"
            body = f"Reminder: Appointment with {appointment_data.get('doctor_name')} tomorrow at {appointment_time_str}"
        else:
            title = "Appointment Soon"
            body = f"Reminder: Appointment with {appointment_data.get('doctor_name')} in 1 hour"

        await NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            title=title,
            body=body,
            data={
                "type": "appointment_reminder",
                "appointment_id": str(appointment_data.get("id")),
                "hours_before": str(hours_before),
                "screen": f"/appointments/{appointment_data.get('id')}",
            },
        )
