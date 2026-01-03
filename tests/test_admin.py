"""Tests for admin endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestAdminUserEndpoints:
    """Tests for admin user management endpoints."""

    async def test_list_users_as_admin(
        self,
        client: AsyncClient,
        admin_token: str,
        db_session: AsyncSession,
    ):
        """Test listing users as admin."""
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["users"], list)

    async def test_list_users_with_filters(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test listing users with role filter."""
        response = await client.get(
            "/api/v1/admin/users",
            params={"role": "patient", "page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data

    async def test_list_users_unauthorized(
        self,
        client: AsyncClient,
        patient_token: str,
    ):
        """Test listing users as non-admin fails."""
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {patient_token}"},
        )

        assert response.status_code == 403

    async def test_list_users_pagination(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test user listing pagination."""
        response = await client.get(
            "/api/v1/admin/users",
            params={"page": 1, "page_size": 5},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5


@pytest.mark.asyncio
class TestAdminAppointmentEndpoints:
    """Tests for admin appointment management endpoints."""

    async def test_list_appointments_as_admin(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test listing appointments as admin."""
        response = await client.get(
            "/api/v1/admin/appointments",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "appointments" in data
        assert "total" in data
        assert isinstance(data["appointments"], list)

    async def test_list_appointments_with_status_filter(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test filtering appointments by status."""
        response = await client.get(
            "/api/v1/admin/appointments",
            params={"status": "confirmed"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "appointments" in data

    async def test_list_appointments_unauthorized(
        self,
        client: AsyncClient,
        patient_token: str,
    ):
        """Test listing appointments as non-admin fails."""
        response = await client.get(
            "/api/v1/admin/appointments",
            headers={"Authorization": f"Bearer {patient_token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestAdminMetricsEndpoint:
    """Tests for admin metrics endpoint."""

    async def test_get_metrics_as_admin(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test getting system metrics as admin."""
        response = await client.get(
            "/api/v1/admin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "appointments" in data
        assert "pharmacies" in data
        assert "notifications" in data

        # Check users metrics structure
        assert "total" in data["users"]
        assert "active" in data["users"]

        # Check appointments metrics structure
        assert "total" in data["appointments"]
        assert "pending" in data["appointments"]
        assert "confirmed" in data["appointments"]

        # Check pharmacies metrics structure
        assert "total" in data["pharmacies"]

        # Check notifications metrics structure
        assert "sent_today" in data["notifications"]

    async def test_get_metrics_unauthorized(
        self,
        client: AsyncClient,
        patient_token: str,
    ):
        """Test getting metrics as non-admin fails."""
        response = await client.get(
            "/api/v1/admin/metrics",
            headers={"Authorization": f"Bearer {patient_token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestAdminNotificationEndpoints:
    """Tests for admin notification endpoints."""

    async def test_get_notification_logs(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test getting notification logs as admin."""
        response = await client.get(
            "/api/v1/admin/notifications/logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["logs"], list)

    async def test_broadcast_notification(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test broadcasting notification to all users."""
        payload = {
            "title": "Test Broadcast",
            "body": "This is a test broadcast notification",
            "target": "all",
        }

        response = await client.post(
            "/api/v1/admin/notifications/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success_count" in data
        assert "failure_count" in data
        assert "total_users" in data
        assert "message" in data

    async def test_broadcast_notification_to_patients(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test broadcasting notification to patients only."""
        payload = {
            "title": "Patient Announcement",
            "body": "Important message for patients",
            "target": "patients",
        }

        response = await client.post(
            "/api/v1/admin/notifications/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200

    async def test_broadcast_notification_unauthorized(
        self,
        client: AsyncClient,
        patient_token: str,
    ):
        """Test broadcasting as non-admin fails."""
        payload = {
            "title": "Test",
            "body": "Test",
            "target": "all",
        }

        response = await client.post(
            "/api/v1/admin/notifications/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {patient_token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestAdminPharmacyEndpoints:
    """Tests for admin pharmacy management endpoints."""

    async def test_verify_pharmacy(
        self,
        client: AsyncClient,
        admin_token: str,
        db_session: AsyncSession,
        test_pharmacy_id: str,
    ):
        """Test verifying a pharmacy."""
        response = await client.patch(
            f"/api/v1/admin/pharmacies/{test_pharmacy_id}/verify",
            params={"is_verified": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True
        assert "id" in data
        assert "name" in data

    async def test_unverify_pharmacy(
        self,
        client: AsyncClient,
        admin_token: str,
        test_pharmacy_id: str,
    ):
        """Test unverifying a pharmacy."""
        response = await client.patch(
            f"/api/v1/admin/pharmacies/{test_pharmacy_id}/verify",
            params={"is_verified": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is False

    async def test_verify_pharmacy_not_found(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test verifying non-existent pharmacy."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.patch(
            f"/api/v1/admin/pharmacies/{fake_id}/verify",
            params={"is_verified": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404

    async def test_verify_pharmacy_unauthorized(
        self,
        client: AsyncClient,
        patient_token: str,
        test_pharmacy_id: str,
    ):
        """Test verifying pharmacy as non-admin fails."""
        response = await client.patch(
            f"/api/v1/admin/pharmacies/{test_pharmacy_id}/verify",
            params={"is_verified": True},
            headers={"Authorization": f"Bearer {patient_token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestAdminAuthRequirement:
    """Tests for admin authentication requirement."""

    async def test_admin_endpoints_require_auth(
        self,
        client: AsyncClient,
    ):
        """Test that admin endpoints require authentication."""
        endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/appointments",
            "/api/v1/admin/metrics",
            "/api/v1/admin/notifications/logs",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401

    async def test_admin_endpoints_reject_expired_token(
        self,
        client: AsyncClient,
    ):
        """Test that admin endpoints reject expired tokens."""
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": "Bearer invalid_token"},
        )

        # Should be 401 or 403 depending on implementation
        assert response.status_code in [401, 403]
