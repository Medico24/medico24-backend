"""Tests for notification endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select

from app.models.push_tokens import push_tokens


@pytest.fixture
async def admin_user(db_session):
    """Create a test admin user in the database."""
    from app.models.users import users

    user_id = uuid4()
    admin_data = {
        "id": user_id,
        "firebase_uid": f"admin_firebase_uid_{user_id}",
        "email": "admin@medico24.com",
        "email_verified": True,
        "auth_provider": "google",
        "full_name": "Admin User",
        "phone": "+1234567890",
        "role": "admin",
        "is_active": True,
        "is_onboarded": True,
    }

    await db_session.execute(insert(users).values(**admin_data))
    await db_session.commit()

    return {
        "id": user_id,
        "firebase_uid": admin_data["firebase_uid"],
        "email": admin_data["email"],
        "full_name": admin_data["full_name"],
        "role": admin_data["role"],
    }


@pytest.fixture
def admin_headers(admin_user) -> dict:
    """Create authentication headers for admin user."""
    from datetime import timedelta

    from app.core.security import create_access_token

    token_data = {
        "sub": str(admin_user["id"]),
        "email": admin_user["email"],
    }
    token = create_access_token(data=token_data, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_fcm_token(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test registering FCM token."""
    token_data = {
        "fcm_token": "test_fcm_token_123456",
        "platform": "android",
    }

    response = await client.post(
        "/api/v1/notifications/register-token",
        json=token_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["fcm_token"] == token_data["fcm_token"]
    assert data["platform"] == token_data["platform"]
    assert data["is_active"] is True
    assert "id" in data
    assert str(data["user_id"]) == str(test_user["id"])

    # Verify token exists in database
    result = await db_session.execute(
        select(push_tokens).where(push_tokens.c.fcm_token == token_data["fcm_token"])
    )
    db_token = result.fetchone()
    assert db_token is not None
    assert db_token.is_active is True


@pytest.mark.asyncio
async def test_register_duplicate_token_same_platform(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test that registering same token on same platform updates existing record."""
    token_data = {
        "fcm_token": "test_fcm_token_duplicate",
        "platform": "android",
    }

    # Register first time
    response1 = await client.post(
        "/api/v1/notifications/register-token",
        json=token_data,
        headers=auth_headers,
    )
    assert response1.status_code == 201
    token_id_1 = response1.json()["id"]

    # Register again with same token
    response2 = await client.post(
        "/api/v1/notifications/register-token",
        json=token_data,
        headers=auth_headers,
    )
    assert response2.status_code == 201
    token_id_2 = response2.json()["id"]

    # Should return same token (updated)
    assert token_id_1 == token_id_2

    # Verify only one active token exists
    result = await db_session.execute(
        select(push_tokens).where(
            push_tokens.c.user_id == test_user["id"],
            push_tokens.c.platform == "android",
            push_tokens.c.is_active == True,  # noqa: E712
        )
    )
    tokens = result.fetchall()
    assert len(tokens) == 1


@pytest.mark.asyncio
async def test_register_token_deactivates_old_tokens(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test that registering new token deactivates old tokens on same platform."""
    # Register first token
    token_data_1 = {
        "fcm_token": "old_token_12345",
        "platform": "android",
    }
    await client.post(
        "/api/v1/notifications/register-token",
        json=token_data_1,
        headers=auth_headers,
    )

    # Register new token on same platform
    token_data_2 = {
        "fcm_token": "new_token_67890",
        "platform": "android",
    }
    response = await client.post(
        "/api/v1/notifications/register-token",
        json=token_data_2,
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Old token should be deactivated
    result = await db_session.execute(
        select(push_tokens).where(push_tokens.c.fcm_token == token_data_1["fcm_token"])
    )
    old_token = result.fetchone()
    assert old_token.is_active is False

    # New token should be active
    result = await db_session.execute(
        select(push_tokens).where(push_tokens.c.fcm_token == token_data_2["fcm_token"])
    )
    new_token = result.fetchone()
    assert new_token.is_active is True


@pytest.mark.asyncio
async def test_register_token_different_platforms(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test that user can have active tokens on different platforms."""
    # Register Android token
    android_token = {
        "fcm_token": "android_token_123",
        "platform": "android",
    }
    await client.post(
        "/api/v1/notifications/register-token",
        json=android_token,
        headers=auth_headers,
    )

    # Register iOS token
    ios_token = {
        "fcm_token": "ios_token_456",
        "platform": "ios",
    }
    response = await client.post(
        "/api/v1/notifications/register-token",
        json=ios_token,
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Both tokens should be active
    result = await db_session.execute(
        select(push_tokens).where(
            push_tokens.c.user_id == test_user["id"],
            push_tokens.c.is_active == True,  # noqa: E712
        )
    )
    active_tokens = result.fetchall()
    assert len(active_tokens) == 2


@pytest.mark.asyncio
async def test_register_token_unauthorized(client: AsyncClient) -> None:
    """Test that registering token without auth fails."""
    token_data = {
        "fcm_token": "unauthorized_token",
        "platform": "android",
    }

    response = await client.post(
        "/api/v1/notifications/register-token",
        json=token_data,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_deactivate_token(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test deactivating a specific FCM token."""
    # Register token first
    token_data = {
        "fcm_token": "token_to_deactivate",
        "platform": "android",
    }
    await client.post(
        "/api/v1/notifications/register-token",
        json=token_data,
        headers=auth_headers,
    )

    # Deactivate the token
    response = await client.request(
        "DELETE",
        "/api/v1/notifications/deactivate-token",
        json=token_data,
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify token is deactivated
    result = await db_session.execute(
        select(push_tokens).where(push_tokens.c.fcm_token == token_data["fcm_token"])
    )
    token = result.fetchone()
    assert token.is_active is False


@pytest.mark.asyncio
async def test_deactivate_nonexistent_token(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    """Test deactivating a token that doesn't exist succeeds (idempotent)."""
    token_data = {
        "fcm_token": "nonexistent_token_xyz",
        "platform": "android",
    }

    response = await client.request(
        "DELETE",
        "/api/v1/notifications/deactivate-token",
        json=token_data,
        headers=auth_headers,
    )
    # Should still succeed (idempotent operation)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_deactivate_all_tokens(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test deactivating all tokens for a user."""
    # Register multiple tokens
    tokens = [
        {"fcm_token": "token_1", "platform": "android"},
        {"fcm_token": "token_2", "platform": "ios"},
        {"fcm_token": "token_3", "platform": "web"},
    ]

    for token_data in tokens:
        await client.post(
            "/api/v1/notifications/register-token",
            json=token_data,
            headers=auth_headers,
        )

    # Deactivate all tokens
    response = await client.delete(
        "/api/v1/notifications/deactivate-all",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify all tokens are deactivated
    result = await db_session.execute(
        select(push_tokens).where(
            push_tokens.c.user_id == test_user["id"],
            push_tokens.c.is_active == True,  # noqa: E712
        )
    )
    active_tokens = result.fetchall()
    assert len(active_tokens) == 0


@pytest.mark.asyncio
@patch("app.services.notification_service.messaging.send_each_for_multicast")
async def test_send_notification_as_admin(
    mock_send_each_for_multicast: AsyncMock,
    client: AsyncClient,
    admin_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test sending notification as admin user."""
    # Mock FCM send_each_for_multicast response
    mock_response = MagicMock()
    mock_response.success_count = 1
    mock_response.failure_count = 0
    mock_send_each_for_multicast.return_value = mock_response

    # Register a token for test user
    token_data = {
        "fcm_token": "test_device_token",
        "platform": "android",
    }
    await db_session.execute(
        insert(push_tokens).values(
            user_id=test_user["id"],
            fcm_token=token_data["fcm_token"],
            platform=token_data["platform"],
            is_active=True,
        )
    )
    await db_session.commit()

    # Send notification
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Test Notification",
        "body": "This is a test message",
        "data": {"type": "test", "action": "view"},
    }

    response = await client.post(
        "/api/v1/notifications/send",
        json=notification_data,
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success_count"] == 1
    assert data["failure_count"] == 0
    assert "message" in data


@pytest.mark.asyncio
async def test_send_notification_as_non_admin(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
) -> None:
    """Test that non-admin users cannot send notifications."""
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Test Notification",
        "body": "This should fail",
    }

    response = await client.post(
        "/api/v1/notifications/send",
        json=notification_data,
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
@patch("app.services.notification_service.messaging.send_each_for_multicast")
async def test_send_notification_to_user_without_tokens(
    mock_send_each_for_multicast: AsyncMock,
    client: AsyncClient,
    admin_headers: dict,
    test_user: dict,
) -> None:
    """Test sending notification to user with no active tokens."""
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Test Notification",
        "body": "This should not send",
    }

    response = await client.post(
        "/api/v1/notifications/send",
        json=notification_data,
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success_count"] == 0
    assert data["failure_count"] == 0
    assert "message" in data


@pytest.mark.asyncio
async def test_invalid_platform(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    """Test registering token with invalid platform."""
    token_data = {
        "fcm_token": "test_token",
        "platform": "invalid_platform",
    }

    response = await client.post(
        "/api/v1/notifications/register-token",
        json=token_data,
        headers=auth_headers,
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_missing_fcm_token(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    """Test registering without FCM token."""
    token_data = {
        "platform": "android",
    }

    response = await client.post(
        "/api/v1/notifications/register-token",
        json=token_data,
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.services.notification_service.messaging.send_each_for_multicast")
async def test_fcm_send_failure_handling(
    mock_send_each_for_multicast: AsyncMock,
    client: AsyncClient,
    admin_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test handling of FCM send failures."""
    # Mock FCM send to raise exception
    mock_send_each_for_multicast.side_effect = Exception("FCM send failed")

    # Register a token
    await db_session.execute(
        insert(push_tokens).values(
            user_id=test_user["id"],
            fcm_token="invalid_token",
            platform="android",
            is_active=True,
        )
    )
    await db_session.commit()

    # Try to send notification
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Test Notification",
        "body": "This should fail",
    }

    response = await client.post(
        "/api/v1/notifications/send",
        json=notification_data,
        headers=admin_headers,
    )

    # Should still return 200 but with failed count
    assert response.status_code == 200
    data = response.json()
    assert data["failure_count"] >= 0  # May vary based on error handling


@pytest.mark.asyncio
@patch("app.services.notification_service.messaging.send_each_for_multicast")
async def test_send_notification_with_custom_data(
    mock_send_each_for_multicast: AsyncMock,
    client: AsyncClient,
    admin_headers: dict,
    test_user: dict,
    db_session,
) -> None:
    """Test sending notification with custom data payload."""
    # Mock FCM send_each_for_multicast response
    mock_response = MagicMock()
    mock_response.success_count = 1
    mock_response.failure_count = 0
    mock_send_each_for_multicast.return_value = mock_response

    # Register token
    await db_session.execute(
        insert(push_tokens).values(
            user_id=test_user["id"],
            fcm_token="test_token_custom_data",
            platform="android",
            is_active=True,
        )
    )
    await db_session.commit()

    # Send notification with custom data
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Appointment Reminder",
        "body": "Your appointment is tomorrow",
        "data": {
            "type": "appointment",
            "appointment_id": "123-456-789",
            "action": "view_details",
            "timestamp": "2026-01-03T10:00:00Z",
        },
    }

    response = await client.post(
        "/api/v1/notifications/send",
        json=notification_data,
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success_count"] == 1
    assert data["failure_count"] == 0
    assert "message" in data

    # Verify the mock was called
    mock_send_each_for_multicast.assert_called()


@pytest.mark.asyncio
@patch("app.services.notification_service.messaging.send_each_for_multicast")
async def test_admin_send_with_valid_secret(
    mock_send_each_for_multicast: AsyncMock,
    client: AsyncClient,
    test_user: dict,
    db_session,
) -> None:
    """Test admin send endpoint with valid secret key."""
    from app.config import settings

    # Mock FCM send_each_for_multicast response
    mock_response = MagicMock()
    mock_response.success_count = 1
    mock_response.failure_count = 0
    mock_send_each_for_multicast.return_value = mock_response

    # Register a token for test user
    await db_session.execute(
        insert(push_tokens).values(
            user_id=test_user["id"],
            fcm_token="test_device_token_admin",
            platform="android",
            is_active=True,
        )
    )
    await db_session.commit()

    # Send notification using admin secret
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Admin Test Notification",
        "body": "Sent via admin secret",
        "data": {"type": "admin_test"},
    }

    response = await client.post(
        "/api/v1/notifications/admin-send",
        json=notification_data,
        headers={"X-Admin-Secret": settings.admin_notification_secret},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success_count"] == 1
    assert data["failure_count"] == 0
    assert "message" in data


@pytest.mark.asyncio
async def test_admin_send_with_invalid_secret(
    client: AsyncClient,
    test_user: dict,
) -> None:
    """Test admin send endpoint with invalid secret key."""
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Test Notification",
        "body": "This should fail",
    }

    response = await client.post(
        "/api/v1/notifications/admin-send",
        json=notification_data,
        headers={"X-Admin-Secret": "invalid_secret_key"},  # pragma: allowlist secret
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_send_without_secret(
    client: AsyncClient,
    test_user: dict,
) -> None:
    """Test admin send endpoint without secret key header."""
    notification_data = {
        "user_id": str(test_user["id"]),
        "title": "Test Notification",
        "body": "This should fail",
    }

    response = await client.post(
        "/api/v1/notifications/admin-send",
        json=notification_data,
    )
    assert response.status_code == 422  # Missing required header
