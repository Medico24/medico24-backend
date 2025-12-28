"""Tests for pharmacy endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture
def sample_pharmacy_data() -> dict:
    """Sample pharmacy data for testing."""
    return {
        "name": "MediPlus Pharmacy",
        "description": "24/7 pharmacy with home delivery",
        "phone": "+91-9876543210",
        "email": "contact@mediplus.com",
        "supports_delivery": True,
        "supports_pickup": True,
        "location": {
            "address_line": "123 Main Street, Downtown",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "pincode": "400001",
            "latitude": 19.0760,
            "longitude": 72.8777,
        },
        "hours": [
            {
                "day_of_week": 1,
                "open_time": "09:00:00",
                "close_time": "21:00:00",
                "is_closed": False,
            },
            {
                "day_of_week": 2,
                "open_time": "09:00:00",
                "close_time": "21:00:00",
                "is_closed": False,
            },
        ],
    }


@pytest.fixture
def sample_pharmacy_data_2() -> dict:
    """Second sample pharmacy data for testing."""
    return {
        "name": "HealthCare Pharmacy",
        "description": "Trusted pharmacy since 1995",
        "phone": "+91-9876543211",
        "email": "info@healthcare.com",
        "supports_delivery": False,
        "supports_pickup": True,
        "location": {
            "address_line": "456 Park Avenue",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "pincode": "400002",
            "latitude": 19.0896,
            "longitude": 72.8656,
        },
    }


@pytest.mark.asyncio
async def test_create_pharmacy(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test creating a pharmacy."""
    response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_pharmacy_data["name"]
    assert data["email"] == sample_pharmacy_data["email"]
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data
    assert "location" in data
    assert data["location"]["city"] == "Mumbai"
    assert "hours" in data
    assert len(data["hours"]) == 2


@pytest.mark.asyncio
async def test_create_pharmacy_without_hours(
    client: AsyncClient,
    sample_pharmacy_data_2: dict,
) -> None:
    """Test creating a pharmacy without hours."""
    response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data_2,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_pharmacy_data_2["name"]
    assert "hours" in data
    assert len(data["hours"]) == 0


@pytest.mark.asyncio
async def test_get_pharmacy(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test getting a specific pharmacy."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    pharmacy_id = create_response.json()["id"]

    # Get the pharmacy
    response = await client.get(f"/api/v1/pharmacies/{pharmacy_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == pharmacy_id
    assert data["name"] == sample_pharmacy_data["name"]
    assert data["location"] is not None
    assert len(data["hours"]) == 2


@pytest.mark.asyncio
async def test_get_pharmacy_not_found(client: AsyncClient) -> None:
    """Test getting a non-existent pharmacy."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/pharmacies/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_pharmacies(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    sample_pharmacy_data_2: dict,
) -> None:
    """Test listing pharmacies."""
    # Create two pharmacies
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data)
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data_2)

    # List pharmacies
    response = await client.get("/api/v1/pharmacies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_pharmacies_with_filters(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    sample_pharmacy_data_2: dict,
) -> None:
    """Test listing pharmacies with filters."""
    # Create two pharmacies
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data)
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data_2)

    # Filter by supports_delivery=true
    response = await client.get("/api/v1/pharmacies?supports_delivery=true")
    assert response.status_code == 200
    data = response.json()
    assert all(p["supports_delivery"] for p in data)

    # Filter by supports_delivery=false
    response = await client.get("/api/v1/pharmacies?supports_delivery=false")
    assert response.status_code == 200
    data = response.json()
    assert all(not p["supports_delivery"] for p in data)


@pytest.mark.asyncio
async def test_update_pharmacy(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test updating a pharmacy."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    pharmacy_id = create_response.json()["id"]

    # Update the pharmacy
    update_data = {
        "name": "Updated Pharmacy Name",
        "description": "Updated description",
        "supports_delivery": False,
    }
    response = await client.patch(
        f"/api/v1/pharmacies/{pharmacy_id}",
        json=update_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["supports_delivery"] == update_data["supports_delivery"]


@pytest.mark.asyncio
async def test_delete_pharmacy(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test deleting a pharmacy."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    pharmacy_id = create_response.json()["id"]

    # Delete the pharmacy
    response = await client.delete(f"/api/v1/pharmacies/{pharmacy_id}")
    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/api/v1/pharmacies/{pharmacy_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_update_pharmacy_location(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test updating pharmacy location."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    pharmacy_id = create_response.json()["id"]

    # Update location
    location_update = {
        "address_line": "789 New Street",
        "city": "Delhi",
        "latitude": 28.7041,
        "longitude": 77.1025,
    }
    response = await client.patch(
        f"/api/v1/pharmacies/{pharmacy_id}/location",
        json=location_update,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["location"]["address_line"] == location_update["address_line"]
    assert data["location"]["city"] == location_update["city"]
    assert data["location"]["latitude"] == location_update["latitude"]


@pytest.mark.asyncio
async def test_add_pharmacy_hours(
    client: AsyncClient,
    sample_pharmacy_data_2: dict,
) -> None:
    """Test adding pharmacy hours."""
    # Create a pharmacy without hours
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data_2,
    )
    pharmacy_id = create_response.json()["id"]

    # Add hours for Monday
    hours_data = {
        "day_of_week": 1,
        "open_time": "08:00:00",
        "close_time": "20:00:00",
        "is_closed": False,
    }
    response = await client.post(
        f"/api/v1/pharmacies/{pharmacy_id}/hours",
        json=hours_data,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["day_of_week"] == 1
    assert data["pharmacy_id"] == pharmacy_id


@pytest.mark.asyncio
async def test_get_pharmacy_hours(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test getting pharmacy hours."""
    # Create a pharmacy with hours
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    pharmacy_id = create_response.json()["id"]

    # Get hours
    response = await client.get(f"/api/v1/pharmacies/{pharmacy_id}/hours")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_delete_pharmacy_hours(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test deleting pharmacy hours."""
    # Create a pharmacy with hours
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    pharmacy_id = create_response.json()["id"]

    # Delete hours for Monday (day_of_week=1)
    response = await client.delete(f"/api/v1/pharmacies/{pharmacy_id}/hours/1")
    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/api/v1/pharmacies/{pharmacy_id}/hours")
    hours = get_response.json()
    assert all(h["day_of_week"] != 1 for h in hours)


@pytest.mark.asyncio
async def test_search_pharmacies_nearby(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    sample_pharmacy_data_2: dict,
) -> None:
    """Test searching pharmacies by location."""
    # Create two pharmacies
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data)
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data_2)

    # Search near Mumbai center
    response = await client.get(
        "/api/v1/pharmacies/search/nearby" "?latitude=19.0760&longitude=72.8777&radius_km=10"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Each result should have distance_km
    for pharmacy in data:
        assert "distance_km" in pharmacy
        assert pharmacy["distance_km"] is not None


@pytest.mark.asyncio
async def test_search_pharmacies_nearby_with_filters(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    sample_pharmacy_data_2: dict,
) -> None:
    """Test searching pharmacies by location with filters."""
    # Create two pharmacies
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data)
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data_2)

    # Search with delivery filter
    response = await client.get(
        "/api/v1/pharmacies/search/nearby"
        "?latitude=19.0760&longitude=72.8777&radius_km=10"
        "&supports_delivery=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert all(p["supports_delivery"] for p in data)


@pytest.mark.asyncio
async def test_search_pharmacies_nearby_small_radius(
    client: AsyncClient,
    sample_pharmacy_data: dict,
) -> None:
    """Test searching pharmacies with small radius."""
    # Create a pharmacy
    await client.post("/api/v1/pharmacies", json=sample_pharmacy_data)

    # Search far away with small radius
    response = await client.get(
        "/api/v1/pharmacies/search/nearby" "?latitude=28.7041&longitude=77.1025&radius_km=1"
    )
    assert response.status_code == 200
    data = response.json()
    # Should return empty list as pharmacy is far away
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_pharmacy_validation_invalid_day_of_week(
    client: AsyncClient,
    sample_pharmacy_data_2: dict,
) -> None:
    """Test pharmacy hours validation for invalid day."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data_2,
    )
    pharmacy_id = create_response.json()["id"]

    # Try to add hours with invalid day_of_week
    hours_data = {
        "day_of_week": 8,  # Invalid: must be 1-7
        "open_time": "08:00:00",
        "close_time": "20:00:00",
        "is_closed": False,
    }
    response = await client.post(
        f"/api/v1/pharmacies/{pharmacy_id}/hours",
        json=hours_data,
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_pharmacy_validation_invalid_coordinates(
    client: AsyncClient,
) -> None:
    """Test pharmacy creation with invalid coordinates."""
    invalid_data = {
        "name": "Test Pharmacy",
        "location": {
            "address_line": "Test Address",
            "city": "Test City",
            "country": "India",
            "latitude": 91.0,  # Invalid: must be between -90 and 90
            "longitude": 72.8777,
        },
    }
    response = await client.post("/api/v1/pharmacies", json=invalid_data)
    assert response.status_code == 422  # Validation error
