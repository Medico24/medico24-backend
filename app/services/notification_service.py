"""Notification service for sending push notifications via FCM."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from firebase_admin import messaging
from sqlalchemy import delete, desc, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import notification_deliveries, notifications
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
        user_id: str | UUID,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        notification_type: str = "other",
        priority: str = "normal",
    ) -> tuple[int, int]:
        """
        Send notification to all active devices of a user.

        Args:
            db: Database session
            user_id: User ID
            title: Notification title
            body: Notification body
            data: Optional data payload
            notification_type: Type of notification (appointment_reminder, etc.)
            priority: Priority level (low, normal, high, urgent)

        Returns:
            Tuple of (success_count, failure_count)
        """
        # Convert user_id to UUID if string
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        # Create notification record
        notification_insert = notifications.insert().values(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            priority=priority,
            data=data,
            status="pending",
        )
        result = await db.execute(notification_insert)
        notification_id = result.inserted_primary_key[0]

        # Get all active tokens for user with their IDs
        query = select(
            push_tokens.c.id,
            push_tokens.c.fcm_token,
        ).where(
            push_tokens.c.user_id == user_id,
            push_tokens.c.is_active == True,  # noqa: E712
        )

        result = await db.execute(query)
        token_records = result.fetchall()

        if not token_records:
            logger.warning("no_active_tokens_for_user", user_id=str(user_id))
            # Update notification status to failed
            await db.execute(
                update(notifications)
                .where(notifications.c.id == notification_id)
                .values(
                    status="failed",
                    failure_reason="No active tokens for user",
                )
            )
            await db.commit()
            return 0, 0

        # Extract tokens and create token mapping
        token_map = {record.fcm_token: record.id for record in token_records}
        fcm_tokens = list(token_map.keys())

        # Create delivery records for each token
        delivery_inserts = [
            {
                "notification_id": notification_id,
                "push_token_id": token_id,
                "delivery_status": "pending",
            }
            for token_id in token_map.values()
        ]
        await db.execute(insert(notification_deliveries).values(delivery_inserts))

        # Update notification status to sent
        await db.execute(
            update(notifications)
            .where(notifications.c.id == notification_id)
            .values(status="sent", sent_at=datetime.now(UTC))
        )
        await db.commit()

        # Send via FCM
        try:
            success_count, failure_count = await NotificationService.send_push_notification(
                tokens=fcm_tokens,
                title=title,
                body=body,
                data=data,
            )

            # Update notification final status
            if failure_count == 0:
                final_status = "delivered"
            elif success_count == 0:
                final_status = "failed"
            else:
                final_status = "delivered"  # Partial success

            await db.execute(
                update(notifications)
                .where(notifications.c.id == notification_id)
                .values(
                    status=final_status,
                    delivered_at=datetime.now(UTC) if success_count > 0 else None,
                )
            )

            # Update delivery records (simplified - mark all as sent for now)
            # In production, you'd parse FCM response to update individual deliveries
            await db.execute(
                update(notification_deliveries)
                .where(notification_deliveries.c.notification_id == notification_id)
                .values(
                    delivery_status="sent",
                    delivered_at=datetime.now(UTC),
                )
            )
            await db.commit()

            return success_count, failure_count

        except Exception as e:
            logger.error(
                "notification_send_failed",
                error=str(e),
                notification_id=str(notification_id),
            )
            # Update notification status to failed
            await db.execute(
                update(notifications)
                .where(notifications.c.id == notification_id)
                .values(
                    status="failed",
                    failure_reason=str(e),
                )
            )
            # Update all deliveries to failed
            await db.execute(
                update(notification_deliveries)
                .where(notification_deliveries.c.notification_id == notification_id)
                .values(
                    delivery_status="failed",
                    failure_reason=str(e),
                )
            )
            await db.commit()
            return 0, len(fcm_tokens)

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
            notification_type="appointment_confirmation",
            priority="normal",
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

        # Determine notification type based on status
        if new_status == "cancelled":
            notification_type = "appointment_cancelled"
            priority = "high"
        elif new_status == "confirmed":
            notification_type = "appointment_confirmation"
            priority = "normal"
        else:
            notification_type = "other"
            priority = "normal"

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
            notification_type=notification_type,
            priority=priority,
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
            priority = "normal"
        else:
            title = "Appointment Soon"
            body = f"Reminder: Appointment with {appointment_data.get('doctor_name')} in 1 hour"
            priority = "high"

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
            notification_type="appointment_reminder",
            priority=priority,
        )

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: str | UUID,
        page: int = 1,
        page_size: int = 50,
        status_filter: str | None = None,
        notification_type_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Get notification history for a user.

        Args:
            db: Database session
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status_filter: Filter by status (optional)
            notification_type_filter: Filter by type (optional)

        Returns:
            Dictionary with notifications list and pagination info
        """
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        # Build query
        query = select(notifications).where(notifications.c.user_id == user_id)

        if status_filter:
            query = query.where(notifications.c.status == status_filter)

        if notification_type_filter:
            query = query.where(notifications.c.notification_type == notification_type_filter)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(desc(notifications.c.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        result = await db.execute(query)
        notification_records = [dict(row._mapping) for row in result.fetchall()]

        return {
            "notifications": notification_records,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_notification_by_id(
        db: AsyncSession,
        notification_id: str | UUID,
        user_id: str | UUID | None = None,
    ) -> dict[str, Any] | None:
        """
        Get notification details by ID with delivery information.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: Optional user ID for access control

        Returns:
            Notification with delivery details or None if not found
        """
        if isinstance(notification_id, str):
            notification_id = UUID(notification_id)
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        # Get notification
        query = select(notifications).where(notifications.c.id == notification_id)
        if user_id:
            query = query.where(notifications.c.user_id == user_id)

        result = await db.execute(query)
        notification = result.fetchone()

        if not notification:
            return None

        notification_dict = dict(notification._mapping)

        # Get delivery information
        delivery_query = select(notification_deliveries).where(
            notification_deliveries.c.notification_id == notification_id
        )
        delivery_result = await db.execute(delivery_query)
        deliveries = [dict(row._mapping) for row in delivery_result.fetchall()]

        # Calculate stats
        total_devices = len(deliveries)
        successful_deliveries = sum(
            1 for d in deliveries if d["delivery_status"] in ["sent", "delivered"]
        )
        failed_deliveries = sum(
            1 for d in deliveries if d["delivery_status"] in ["failed", "invalid_token"]
        )

        return {
            "notification": notification_dict,
            "deliveries": deliveries,
            "total_devices": total_devices,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
        }

    @staticmethod
    async def mark_notification_as_read(
        db: AsyncSession,
        notification_id: str | UUID,
        user_id: str | UUID,
    ) -> bool:
        """
        Mark a notification as read.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID for verification

        Returns:
            True if updated, False if not found
        """
        if isinstance(notification_id, str):
            notification_id = UUID(notification_id)
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        result = await db.execute(
            update(notifications)
            .where(
                notifications.c.id == notification_id,
                notifications.c.user_id == user_id,
            )
            .values(
                read_at=datetime.now(UTC),
                status="read",
                updated_at=datetime.now(UTC),
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def delete_notification(
        db: AsyncSession,
        notification_id: str | UUID,
        user_id: str | UUID | None = None,
    ) -> bool:
        """
        Delete a notification (admin or user).

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: Optional user ID for access control (non-admin)

        Returns:
            True if deleted, False if not found
        """
        if isinstance(notification_id, str):
            notification_id = UUID(notification_id)
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        query = delete(notifications).where(notifications.c.id == notification_id)
        if user_id:
            query = query.where(notifications.c.user_id == user_id)

        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_notification_stats(
        db: AsyncSession,
        user_id: str | UUID | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get notification statistics.

        Args:
            db: Database session
            user_id: Optional user ID to filter stats
            days: Number of days to look back

        Returns:
            Statistics dictionary
        """
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        # Base query
        query = select(notifications).where(notifications.c.created_at >= cutoff_date)
        if user_id:
            query = query.where(notifications.c.user_id == user_id)

        result = await db.execute(query)
        all_notifications = result.fetchall()

        total = len(all_notifications)
        by_status = {}
        by_type = {}
        by_priority = {}

        for notif in all_notifications:
            status = notif.status
            ntype = notif.notification_type
            priority = notif.priority

            by_status[status] = by_status.get(status, 0) + 1
            by_type[ntype] = by_type.get(ntype, 0) + 1
            by_priority[priority] = by_priority.get(priority, 0) + 1

        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_priority": by_priority,
            "days": days,
        }
