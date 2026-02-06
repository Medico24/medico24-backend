"""Tests for clinic endpoints and service layer."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctors import doctors
from app.models.users import users


@pytest.fixture
def sample_clinic_data() -> dict:
    """Sample clinic data for testing."""
    return {
        "name": "City Medical Center",
        "description": "Multi-specialty 24/7 medical center",
        "logo_url": "https://example.com/logo.png",
        "contacts": {
            "phone_primary": "+91-9876543210",
            "phone_secondary": "+91-9876543211",
            "email": "contact@citymedical.com",
            "website": "https://citymedical.com",
        },
        "address": "123 Main Street, Downtown, Mumbai, Maharashtra 400001",
        "latitude": "19.0760",
        "longitude": "72.8777",
        "opening_hours": {
            "monday": {"open": "08:00", "close": "20:00"},
            "tuesday": {"open": "08:00", "close": "20:00"},
            "wednesday": {"open": "08:00", "close": "20:00"},
            "thursday": {"open": "08:00", "close": "20:00"},
            "friday": {"open": "08:00", "close": "20:00"},
            "saturday": {"open": "09:00", "close": "18:00"},
            "sunday": {"open": "10:00", "close": "16:00"},
        },
    }


@pytest.fixture
def sample_clinic_data_2() -> dict:
    """Second sample clinic data for testing."""
    return {
        "name": "HealthCare Clinic",
        "description": "Family healthcare clinic",
        "contacts": {
            "phone_primary": "+91-9876543212",
            "email": "info@healthcare.com",
        },
        "address": "456 Park Avenue, Andheri, Mumbai, Maharashtra 400058",
        "latitude": "19.1136",
        "longitude": "72.8697",
    }


# ============================================================================
# Clinic CRUD Endpoint Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_clinic(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test creating a clinic."""
    response = await client.post(
        "/api/v1/clinics/",
        json=sample_clinic_data,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_clinic_data["name"]
    assert data["slug"] == "city-medical-center"
    assert data["description"] == sample_clinic_data["description"]
    assert data["contacts"] == sample_clinic_data["contacts"]
    assert data["address"] == sample_clinic_data["address"]
    assert data["is_active"] is True
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_clinic_with_custom_slug(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test creating a clinic with custom slug."""
    sample_clinic_data["slug"] = "custom-clinic-slug"
    response = await client.post(
        "/api/v1/clinics/",
        json=sample_clinic_data,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "custom-clinic-slug"


@pytest.mark.asyncio
async def test_create_clinic_duplicate_slug(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test creating clinic with duplicate slug fails."""
    # Create first clinic
    await client.post("/api/v1/clinics/", json=sample_clinic_data)

    # Try to create second with same slug
    sample_clinic_data["name"] = "Another Clinic"
    sample_clinic_data["slug"] = "city-medical-center"
    response = await client.post("/api/v1/clinics/", json=sample_clinic_data)

    assert response.status_code == 400
    assert "slug" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_clinic_by_id(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test getting a clinic by ID."""
    # Create clinic
    create_response = await client.post(
        "/api/v1/clinics/",
        json=sample_clinic_data,
    )
    clinic_id = create_response.json()["id"]

    # Get clinic
    response = await client.get(f"/api/v1/clinics/{clinic_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == clinic_id
    assert data["name"] == sample_clinic_data["name"]


@pytest.mark.asyncio
async def test_get_clinic_by_id_not_found(client: AsyncClient) -> None:
    """Test getting non-existent clinic returns 404."""
    response = await client.get("/api/v1/clinics/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_clinic_by_slug(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test getting a clinic by slug."""
    # Create clinic
    await client.post("/api/v1/clinics/", json=sample_clinic_data)

    # Get clinic by slug
    response = await client.get("/api/v1/clinics/slug/city-medical-center")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "city-medical-center"
    assert data["name"] == sample_clinic_data["name"]


@pytest.mark.asyncio
async def test_list_clinics(
    client: AsyncClient,
    sample_clinic_data: dict,
    sample_clinic_data_2: dict,
) -> None:
    """Test listing clinics."""
    # Create two clinics
    await client.post("/api/v1/clinics/", json=sample_clinic_data)
    await client.post("/api/v1/clinics/", json=sample_clinic_data_2)

    # List clinics
    response = await client.get("/api/v1/clinics/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_clinics_with_filters(
    client: AsyncClient,
    sample_clinic_data: dict,
    sample_clinic_data_2: dict,
) -> None:
    """Test listing clinics with filters."""
    # Create clinics
    await client.post("/api/v1/clinics/", json=sample_clinic_data)
    await client.post("/api/v1/clinics/", json=sample_clinic_data_2)

    # Filter by name
    response = await client.get("/api/v1/clinics/?name_search=City")
    assert response.status_code == 200
    data = response.json()
    assert all("City" in clinic["name"] for clinic in data)

    # Filter by active status
    response = await client.get("/api/v1/clinics/?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert all(clinic["is_active"] is True for clinic in data)


@pytest.mark.asyncio
async def test_search_clinics(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test searching clinics."""
    await client.post("/api/v1/clinics/", json=sample_clinic_data)

    response = await client.get("/api/v1/clinics/search?name_search=Medical")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_search_nearby_clinics(
    client: AsyncClient,
    sample_clinic_data: dict,
    sample_clinic_data_2: dict,
) -> None:
    """Test searching clinics near a location."""
    # Create clinics at different locations
    await client.post("/api/v1/clinics/", json=sample_clinic_data)
    await client.post("/api/v1/clinics/", json=sample_clinic_data_2)

    # Search near first clinic location
    response = await client.get(
        "/api/v1/clinics/nearby?" "latitude=19.0760&longitude=72.8777&radius_km=5"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Should have distance_km field
    if data:
        assert "distance_km" in data[0]


@pytest.mark.asyncio
async def test_update_clinic(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test updating a clinic."""
    # Create clinic
    create_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = create_response.json()["id"]

    # Update clinic
    update_data = {
        "name": "Updated Medical Center",
        "description": "Updated description",
    }
    response = await client.put(f"/api/v1/clinics/{clinic_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Medical Center"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_clinic_not_found(client: AsyncClient) -> None:
    """Test updating non-existent clinic returns 404."""
    response = await client.put(
        "/api/v1/clinics/00000000-0000-0000-0000-000000000000",
        json={"name": "Test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_clinic(
    client: AsyncClient,
    sample_clinic_data: dict,
) -> None:
    """Test soft deleting a clinic."""
    # Create clinic
    create_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = create_response.json()["id"]

    # Delete clinic
    response = await client.delete(f"/api/v1/clinics/{clinic_id}")
    assert response.status_code == 204

    # Verify clinic is soft deleted (should not appear in list)
    response = await client.get(f"/api/v1/clinics/{clinic_id}")
    assert response.status_code == 404


# ============================================================================
# Doctor-Clinic Association Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_doctor_to_clinic(
    client: AsyncClient,
    sample_clinic_data: dict,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    """Test adding a doctor to a clinic."""
    # Create clinic
    clinic_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = clinic_response.json()["id"]

    # Create user and doctor
    user_query = select(users).limit(1)
    result = await db_session.execute(user_query)
    user = result.mappings().first()

    if not user:
        # Create a test user if none exists
        user_data = {
            "phone_number": "+919876543210",
            "full_name": "Dr. Test Doctor",
            "email": "doctor@test.com",
            "role": "doctor",
        }
        result = await db_session.execute(users.insert().values(**user_data).returning(users))
        user = result.mappings().first()
        await db_session.commit()

    # Create doctor
    doctor_data = {
        "user_id": user["id"],
        "license_number": "DOC12345",
        "specialization": "Cardiology",
        "experience_years": 10,
    }
    result = await db_session.execute(doctors.insert().values(**doctor_data).returning(doctors))
    doctor = result.mappings().first()
    await db_session.commit()

    # Add doctor to clinic
    association_data = {
        "doctor_id": str(doctor["id"]),
        "clinic_id": clinic_id,
        "is_primary": True,
        "consultation_fee": 1000.00,
        "consultation_duration_minutes": 30,
        "department": "Cardiology",
        "designation": "Senior Consultant",
        "available_days": [1, 2, 3, 4, 5],
        "available_time_slots": {
            "monday": ["09:00-12:00", "14:00-18:00"],
            "tuesday": ["09:00-12:00", "14:00-18:00"],
        },
        "appointment_booking_enabled": True,
    }

    response = await client.post(
        f"/api/v1/clinics/{clinic_id}/doctors",
        json=association_data,
    )
    assert response.status_code == 201
    data = response.json()
    assert str(data["doctor_id"]) == str(doctor["id"])
    assert data["clinic_id"] == clinic_id
    assert data["is_primary"] is True
    assert float(data["consultation_fee"]) == 1000.00
    assert data["department"] == "Cardiology"


@pytest.mark.asyncio
async def test_get_clinic_doctors(
    client: AsyncClient,
    sample_clinic_data: dict,
    db_session: AsyncSession,
) -> None:
    """Test getting all doctors at a clinic."""
    # Create clinic
    clinic_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = clinic_response.json()["id"]

    # Create and add a doctor
    user_data = {
        "phone_number": "+919876543220",
        "full_name": "Dr. John Smith",
        "email": "john@test.com",
        "role": "doctor",
    }
    result = await db_session.execute(users.insert().values(**user_data).returning(users))
    user = result.mappings().first()
    await db_session.commit()

    doctor_data = {
        "user_id": user["id"],
        "license_number": "DOC54321",
        "specialization": "General Medicine",
        "experience_years": 5,
    }
    result = await db_session.execute(doctors.insert().values(**doctor_data).returning(doctors))
    doctor = result.mappings().first()
    await db_session.commit()

    # Add doctor to clinic
    association_data = {
        "doctor_id": str(doctor["id"]),
        "clinic_id": clinic_id,
        "is_primary": True,
        "consultation_fee": 500.00,
        "department": "General Medicine",
    }
    await client.post(f"/api/v1/clinics/{clinic_id}/doctors", json=association_data)

    # Get doctors at clinic
    response = await client.get(f"/api/v1/clinics/{clinic_id}/doctors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["doctor_name"] == "Dr. John Smith"


@pytest.mark.asyncio
async def test_get_doctor_clinics(
    client: AsyncClient,
    sample_clinic_data: dict,
    sample_clinic_data_2: dict,
    db_session: AsyncSession,
) -> None:
    """Test getting all clinics where a doctor works."""
    # Create two clinics
    clinic1_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic2_response = await client.post("/api/v1/clinics/", json=sample_clinic_data_2)
    clinic1_id = clinic1_response.json()["id"]
    clinic2_id = clinic2_response.json()["id"]

    # Create doctor
    user_data = {
        "phone_number": "+919876543230",
        "full_name": "Dr. Jane Doe",
        "email": "jane@test.com",
        "role": "doctor",
    }
    result = await db_session.execute(users.insert().values(**user_data).returning(users))
    user = result.mappings().first()
    await db_session.commit()

    doctor_data = {
        "user_id": user["id"],
        "license_number": "DOC99999",
        "specialization": "Pediatrics",
        "experience_years": 8,
    }
    result = await db_session.execute(doctors.insert().values(**doctor_data).returning(doctors))
    doctor = result.mappings().first()
    await db_session.commit()

    # Add doctor to both clinics
    for clinic_id, is_primary in [(clinic1_id, True), (clinic2_id, False)]:
        association_data = {
            "doctor_id": str(doctor["id"]),
            "clinic_id": clinic_id,
            "is_primary": is_primary,
            "consultation_fee": 800.00,
            "department": "Pediatrics",
        }
        await client.post(f"/api/v1/clinics/{clinic_id}/doctors", json=association_data)

    # Get clinics for doctor
    response = await client.get(f"/api/v1/clinics/doctors/{doctor['id']}/clinics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Primary clinic should be first
    assert data[0]["is_primary"] is True


@pytest.mark.asyncio
async def test_update_doctor_clinic_association(
    client: AsyncClient,
    sample_clinic_data: dict,
    db_session: AsyncSession,
) -> None:
    """Test updating doctor-clinic association."""
    # Create clinic and doctor
    clinic_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = clinic_response.json()["id"]

    user_data = {
        "phone_number": "+919876543240",
        "full_name": "Dr. Update Test",
        "email": "update@test.com",
        "role": "doctor",
    }
    result = await db_session.execute(users.insert().values(**user_data).returning(users))
    user = result.mappings().first()
    await db_session.commit()

    doctor_data = {
        "user_id": user["id"],
        "license_number": "DOC11111",
        "specialization": "Orthopedics",
        "experience_years": 12,
    }
    result = await db_session.execute(doctors.insert().values(**doctor_data).returning(doctors))
    doctor = result.mappings().first()
    await db_session.commit()

    # Create association
    association_data = {
        "doctor_id": str(doctor["id"]),
        "clinic_id": clinic_id,
        "consultation_fee": 1200.00,
        "department": "Orthopedics",
    }
    assoc_response = await client.post(
        f"/api/v1/clinics/{clinic_id}/doctors",
        json=association_data,
    )
    association_id = assoc_response.json()["id"]

    # Update association
    update_data = {
        "consultation_fee": 1500.00,
        "designation": "Head of Department",
    }
    response = await client.put(
        f"/api/v1/clinics/doctor-associations/{association_id}",
        json=update_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["consultation_fee"]) == 1500.00
    assert data["designation"] == "Head of Department"


@pytest.mark.asyncio
async def test_end_doctor_clinic_association(
    client: AsyncClient,
    sample_clinic_data: dict,
    db_session: AsyncSession,
) -> None:
    """Test ending doctor-clinic association."""
    # Create clinic and doctor
    clinic_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = clinic_response.json()["id"]

    user_data = {
        "phone_number": "+919876543250",
        "full_name": "Dr. End Test",
        "email": "end@test.com",
        "role": "doctor",
    }
    result = await db_session.execute(users.insert().values(**user_data).returning(users))
    user = result.mappings().first()
    await db_session.commit()

    doctor_data = {
        "user_id": user["id"],
        "license_number": "DOC22222",
        "specialization": "Dermatology",
        "experience_years": 7,
    }
    result = await db_session.execute(doctors.insert().values(**doctor_data).returning(doctors))
    doctor = result.mappings().first()
    await db_session.commit()

    # Create association
    association_data = {
        "doctor_id": str(doctor["id"]),
        "clinic_id": clinic_id,
        "consultation_fee": 900.00,
        "department": "Dermatology",
    }
    assoc_response = await client.post(
        f"/api/v1/clinics/{clinic_id}/doctors",
        json=association_data,
    )
    association_id = assoc_response.json()["id"]

    # End association
    response = await client.post(
        f"/api/v1/clinics/doctor-associations/{association_id}/end",
        json={},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["end_date"] is not None
    assert data["status"] == "inactive"


@pytest.mark.asyncio
async def test_remove_doctor_from_clinic(
    client: AsyncClient,
    sample_clinic_data: dict,
    db_session: AsyncSession,
) -> None:
    """Test removing doctor from clinic."""
    # Create clinic and doctor
    clinic_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = clinic_response.json()["id"]

    user_data = {
        "phone_number": "+919876543260",
        "full_name": "Dr. Remove Test",
        "email": "remove@test.com",
        "role": "doctor",
    }
    result = await db_session.execute(users.insert().values(**user_data).returning(users))
    user = result.mappings().first()
    await db_session.commit()

    doctor_data = {
        "user_id": user["id"],
        "license_number": "DOC33333",
        "specialization": "ENT",
        "experience_years": 6,
    }
    result = await db_session.execute(doctors.insert().values(**doctor_data).returning(doctors))
    doctor = result.mappings().first()
    await db_session.commit()

    # Create association
    association_data = {
        "doctor_id": str(doctor["id"]),
        "clinic_id": clinic_id,
        "consultation_fee": 700.00,
        "department": "ENT",
    }
    await client.post(f"/api/v1/clinics/{clinic_id}/doctors", json=association_data)

    # Remove doctor from clinic
    response = await client.delete(f"/api/v1/clinics/{clinic_id}/doctors/{doctor['id']}")
    assert response.status_code == 204

    # Verify doctor no longer active at clinic
    response = await client.get(f"/api/v1/clinics/{clinic_id}/doctors")
    data = response.json()
    active_doctors = [d for d in data if d["doctor_id"] == str(doctor["id"])]
    assert len(active_doctors) == 0


@pytest.mark.asyncio
async def test_duplicate_active_association_prevented(
    client: AsyncClient,
    sample_clinic_data: dict,
    db_session: AsyncSession,
) -> None:
    """Test that duplicate active associations are prevented."""
    # Create clinic and doctor
    clinic_response = await client.post("/api/v1/clinics/", json=sample_clinic_data)
    clinic_id = clinic_response.json()["id"]

    user_data = {
        "phone_number": "+919876543270",
        "full_name": "Dr. Duplicate Test",
        "email": "duplicate@test.com",
        "role": "doctor",
    }
    result = await db_session.execute(users.insert().values(**user_data).returning(users))
    user = result.mappings().first()
    await db_session.commit()

    doctor_data = {
        "user_id": user["id"],
        "license_number": "DOC44444",
        "specialization": "Neurology",
        "experience_years": 15,
    }
    result = await db_session.execute(doctors.insert().values(**doctor_data).returning(doctors))
    doctor = result.mappings().first()
    await db_session.commit()

    # Create first association
    association_data = {
        "doctor_id": str(doctor["id"]),
        "clinic_id": clinic_id,
        "consultation_fee": 1500.00,
        "department": "Neurology",
    }
    await client.post(f"/api/v1/clinics/{clinic_id}/doctors", json=association_data)

    # Try to create duplicate association
    response = await client.post(
        f"/api/v1/clinics/{clinic_id}/doctors",
        json=association_data,
    )
    assert response.status_code == 400
    assert "already associated" in response.json()["detail"].lower()
