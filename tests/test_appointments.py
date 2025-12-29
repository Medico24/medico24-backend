"""Tests for appointment endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_create_appointment(
    client: AsyncClient,
    auth_headers: dict,
    sample_appointment_data: dict,
) -> None:
    """Test creating an appointment."""
    response = await client.post(
        "/api/v1/appointments/",
        json=sample_appointment_data,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["doctor_name"] == sample_appointment_data["doctor_name"]
    assert data["status"] == "scheduled"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_appointments(
    client: AsyncClient,
    auth_headers: dict,
    sample_appointment_data: dict,
) -> None:
    """Test listing appointments."""
    # Create an appointment first
    await client.post(
        "/api/v1/appointments/",
        json=sample_appointment_data,
        headers=auth_headers,
    )

    # List appointments
    response = await client.get(
        "/api/v1/appointments/",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_appointment(
    client: AsyncClient,
    auth_headers: dict,
    sample_appointment_data: dict,
) -> None:
    """Test getting a specific appointment."""
    # Create an appointment
    create_response = await client.post(
        "/api/v1/appointments/",
        json=sample_appointment_data,
        headers=auth_headers,
    )
    appointment_id = create_response.json()["id"]

    # Get the appointment
    response = await client.get(
        f"/api/v1/appointments/{appointment_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == appointment_id
    assert data["doctor_name"] == sample_appointment_data["doctor_name"]


@pytest.mark.asyncio
async def test_update_appointment(
    client: AsyncClient,
    auth_headers: dict,
    sample_appointment_data: dict,
) -> None:
    """Test updating an appointment."""
    # Create an appointment
    create_response = await client.post(
        "/api/v1/appointments/",
        json=sample_appointment_data,
        headers=auth_headers,
    )
    appointment_id = create_response.json()["id"]

    # Update the appointment
    update_data = {"notes": "Updated notes"}
    response = await client.put(
        f"/api/v1/appointments/{appointment_id}",
        json=update_data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_update_appointment_status(
    client: AsyncClient,
    auth_headers: dict,
    sample_appointment_data: dict,
) -> None:
    """Test updating appointment status."""
    # Create an appointment
    create_response = await client.post(
        "/api/v1/appointments/",
        json=sample_appointment_data,
        headers=auth_headers,
    )
    appointment_id = create_response.json()["id"]

    # Update status
    status_data = {"status": "confirmed"}
    response = await client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        json=status_data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"


@pytest.mark.asyncio
async def test_delete_appointment(
    client: AsyncClient,
    auth_headers: dict,
    sample_appointment_data: dict,
) -> None:
    """Test soft deleting an appointment."""
    # Create an appointment
    create_response = await client.post(
        "/api/v1/appointments/",
        json=sample_appointment_data,
        headers=auth_headers,
    )
    appointment_id = create_response.json()["id"]

    # Delete the appointment
    response = await client.delete(
        f"/api/v1/appointments/{appointment_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Try to get the deleted appointment
    get_response = await client.get(
        f"/api/v1/appointments/{appointment_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Test that endpoints require authentication."""
    response = await client.get("/api/v1/appointments/")
    assert response.status_code == 401  # No auth header - Unauthorized


@pytest.mark.asyncio
async def test_invalid_appointment_data(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    """Test creating appointment with invalid data."""
    invalid_data = {
        "doctor_name": "",  # Empty name should fail validation
        "reason": "Test",
        "contact_phone": "123",  # Too short
    }

    response = await client.post(
        "/api/v1/appointments/",
        json=invalid_data,
        headers=auth_headers,
    )
    assert response.status_code == 422  # Validation error
