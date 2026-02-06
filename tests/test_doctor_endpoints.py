"""Tests for doctor endpoints."""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinics import clinics
from app.models.doctor_clinics import doctor_clinics
from app.models.doctors import doctors
from app.models.users import users


@pytest.fixture
async def test_user(db: AsyncSession):
    """Create a test user."""
    user_id = uuid4()
    await db.execute(
        insert(users).values(
            id=user_id,
            email=f"doctor.{user_id}@test.com",
            phone_number="+1234567890",
            password_hash="hashed_password",  # pragma: allowlist secret
            role="doctor",
            full_name="Dr. Test Doctor",
            email_verified=True,
        )
    )
    await db.commit()
    yield user_id
    await db.execute(delete(users).where(users.c.id == user_id))
    await db.commit()


@pytest.fixture
async def test_doctor(db: AsyncSession, test_user):
    """Create a test doctor."""
    doctor_id = uuid4()
    await db.execute(
        insert(doctors).values(
            id=doctor_id,
            user_id=test_user,
            license_number=f"LIC-{uuid4()}",
            specialization="Cardiology",
            sub_specialization="Interventional Cardiology",
            qualification="MBBS, MD (Cardiology), DM (Cardiology)",
            experience_years=10,
            consultation_fee=Decimal("150.00"),
            consultation_duration_minutes=30,
            bio="Experienced cardiologist specializing in interventional procedures",
            languages_spoken=["English", "Spanish"],
            medical_council_registration="MCI123456",
            is_verified=True,
            rating=Decimal("4.5"),
            rating_count=25,
        )
    )
    await db.commit()
    yield doctor_id
    await db.execute(delete(doctors).where(doctors.c.id == doctor_id))
    await db.commit()


@pytest.fixture
async def test_clinic(db: AsyncSession):
    """Create a test clinic."""
    clinic_id = uuid4()
    await db.execute(
        insert(clinics).values(
            id=clinic_id,
            name="Test Cardiac Clinic",
            slug="test-cardiac-clinic",
            address="123 Heart Street, Cardio City",
            latitude=40.7128,
            longitude=-74.0060,
            phone_number="+1234567890",
            email="clinic@test.com",
            operating_hours={"mon": "9:00-17:00", "tue": "9:00-17:00"},
        )
    )
    await db.commit()
    yield clinic_id
    await db.execute(delete(clinics).where(clinics.c.id == clinic_id))
    await db.commit()


# ============================================================================
# Doctor Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_doctor_success(client: AsyncClient, test_user, db: AsyncSession):
    """Test successful doctor creation."""
    doctor_data = {
        "user_id": str(test_user),
        "license_number": f"LIC-{uuid4()}",
        "specialization": "Neurology",
        "sub_specialization": "Pediatric Neurology",
        "qualification": "MBBS, MD (Neurology)",
        "experience_years": 8,
        "consultation_fee": 120.50,
        "consultation_duration_minutes": 45,
        "bio": "Specialized in pediatric neurological disorders",
        "languages_spoken": ["English", "French"],
        "medical_council_registration": "MCI789012",
    }

    response = await client.post("/api/v1/doctors/", json=doctor_data)

    assert response.status_code == 201
    data = response.json()
    assert data["license_number"] == doctor_data["license_number"]
    assert data["specialization"] == doctor_data["specialization"]
    assert data["user_id"] == doctor_data["user_id"]
    assert data["is_verified"] is False  # New doctors should not be verified

    # Cleanup
    await db.execute(delete(doctors).where(doctors.c.id == data["id"]))
    await db.commit()


@pytest.mark.asyncio
async def test_create_doctor_duplicate_license(client: AsyncClient, test_doctor, test_user):
    """Test creating doctor with duplicate license number."""
    # Get existing doctor's license number
    response = await client.get(f"/api/v1/doctors/{test_doctor}")
    existing_license = response.json()["license_number"]

    # Try to create another doctor with same license
    new_user_id = uuid4()
    doctor_data = {
        "user_id": str(new_user_id),
        "license_number": existing_license,
        "specialization": "Orthopedics",
    }

    response = await client.post("/api/v1/doctors/", json=doctor_data)

    assert response.status_code == 400
    assert "license number" in response.json()["detail"].lower()


# ============================================================================
# Doctor Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_doctor_by_id(client: AsyncClient, test_doctor):
    """Test getting doctor by ID."""
    response = await client.get(f"/api/v1/doctors/{test_doctor}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_doctor)
    assert data["specialization"] == "Cardiology"
    assert "full_name" in data
    assert "clinics" in data


@pytest.mark.asyncio
async def test_get_doctor_not_found(client: AsyncClient):
    """Test getting non-existent doctor."""
    fake_id = uuid4()
    response = await client.get(f"/api/v1/doctors/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_doctor_by_user_id(client: AsyncClient, test_user, test_doctor):
    """Test getting doctor by user ID."""
    response = await client.get(f"/api/v1/doctors/user/{test_user}")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user)
    assert data["id"] == str(test_doctor)


# ============================================================================
# Doctor Listing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_doctors(client: AsyncClient, test_doctor):
    """Test listing all doctors."""
    response = await client.get("/api/v1/doctors/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Find our test doctor
    doctor_ids = [d["id"] for d in data]
    assert str(test_doctor) in doctor_ids


@pytest.mark.asyncio
async def test_list_doctors_with_pagination(client: AsyncClient, test_doctor):
    """Test listing doctors with pagination."""
    response = await client.get("/api/v1/doctors/?skip=0&limit=5")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


@pytest.mark.asyncio
async def test_list_doctors_filter_by_specialization(client: AsyncClient, test_doctor):
    """Test filtering doctors by specialization."""
    response = await client.get("/api/v1/doctors/?specialization=Cardiology")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # All results should have Cardiology specialization
    for doctor in data:
        assert "cardiology" in doctor["specialization"].lower()


@pytest.mark.asyncio
async def test_list_doctors_filter_by_verification(client: AsyncClient, test_doctor):
    """Test filtering doctors by verification status."""
    response = await client.get("/api/v1/doctors/?is_verified=true")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # All results should be verified
    for doctor in data:
        assert doctor["is_verified"] is True


@pytest.mark.asyncio
async def test_list_doctors_filter_by_experience(client: AsyncClient, test_doctor):
    """Test filtering doctors by experience range."""
    response = await client.get("/api/v1/doctors/?min_experience=5&max_experience=15")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # All results should be within experience range
    for doctor in data:
        if doctor["experience_years"]:
            assert 5 <= doctor["experience_years"] <= 15


@pytest.mark.asyncio
async def test_list_doctors_filter_by_rating(client: AsyncClient, test_doctor):
    """Test filtering doctors by minimum rating."""
    response = await client.get("/api/v1/doctors/?min_rating=4.0")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # All results should meet minimum rating
    for doctor in data:
        if doctor["rating"]:
            assert float(doctor["rating"]) >= 4.0


# ============================================================================
# Doctor Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_doctors(client: AsyncClient, test_doctor):
    """Test searching doctors with filters."""
    response = await client.get("/api/v1/doctors/search?specialization=Cardiology&is_verified=true")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_nearby_doctors(
    client: AsyncClient, test_doctor, test_clinic, db: AsyncSession
):
    """Test searching for nearby doctors through clinic locations."""
    # Associate doctor with clinic
    await db.execute(
        insert(doctor_clinics).values(
            doctor_id=test_doctor,
            clinic_id=test_clinic,
            status="active",
            appointment_booking_enabled=True,
        )
    )
    await db.commit()

    # Search nearby (using clinic coordinates +/- small delta)
    response = await client.get(
        "/api/v1/doctors/nearby?latitude=40.7128&longitude=-74.0060&radius_km=10"
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Cleanup
    await db.execute(
        delete(doctor_clinics).where(
            (doctor_clinics.c.doctor_id == test_doctor)
            & (doctor_clinics.c.clinic_id == test_clinic)
        )
    )
    await db.commit()


# ============================================================================
# Doctor Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_doctor(client: AsyncClient, test_doctor):
    """Test updating doctor information."""
    update_data = {
        "specialization": "Cardiology",
        "sub_specialization": "Electrophysiology",
        "experience_years": 12,
        "consultation_fee": 175.00,
        "bio": "Updated bio for cardiac electrophysiologist",
    }

    response = await client.put(f"/api/v1/doctors/{test_doctor}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["sub_specialization"] == update_data["sub_specialization"]
    assert data["experience_years"] == update_data["experience_years"]
    assert float(data["consultation_fee"]) == update_data["consultation_fee"]


@pytest.mark.asyncio
async def test_update_doctor_not_found(client: AsyncClient):
    """Test updating non-existent doctor."""
    fake_id = uuid4()
    update_data = {"specialization": "Dermatology"}

    response = await client.put(f"/api/v1/doctors/{fake_id}", json=update_data)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_doctor_partial(client: AsyncClient, test_doctor):
    """Test partial update of doctor."""
    update_data = {"bio": "Updated biography only"}

    response = await client.put(f"/api/v1/doctors/{test_doctor}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == update_data["bio"]
    # Other fields should remain unchanged
    assert data["specialization"] == "Cardiology"


# ============================================================================
# Doctor Verification Tests
# ============================================================================


@pytest.mark.asyncio
async def test_verify_doctor(client: AsyncClient, db: AsyncSession, test_user):
    """Test verifying a doctor."""
    # Create unverified doctor
    doctor_id = uuid4()
    await db.execute(
        insert(doctors).values(
            id=doctor_id,
            user_id=test_user,
            license_number=f"LIC-{uuid4()}",
            specialization="Dermatology",
            is_verified=False,
        )
    )
    await db.commit()

    # Verify doctor
    admin_id = uuid4()
    verification_data = {"verification_documents": {"doc_type": "license", "doc_id": "123456"}}

    response = await client.post(
        f"/api/v1/doctors/{doctor_id}/verify?verified_by={admin_id}", json=verification_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_verified"] is True
    assert data["verified_by"] == str(admin_id)
    assert data["verified_at"] is not None

    # Cleanup
    await db.execute(delete(doctors).where(doctors.c.id == doctor_id))
    await db.commit()


@pytest.mark.asyncio
async def test_unverify_doctor(client: AsyncClient, test_doctor):
    """Test removing verification from a doctor."""
    # First verify the doctor is verified
    response = await client.get(f"/api/v1/doctors/{test_doctor}")
    assert response.json()["is_verified"] is True

    # Unverify
    response = await client.post(f"/api/v1/doctors/{test_doctor}/unverify")

    assert response.status_code == 200
    data = response.json()
    assert data["is_verified"] is False
    assert data["verified_at"] is None
    assert data["verified_by"] is None


@pytest.mark.asyncio
async def test_verify_nonexistent_doctor(client: AsyncClient):
    """Test verifying non-existent doctor."""
    fake_id = uuid4()
    admin_id = uuid4()

    response = await client.post(
        f"/api/v1/doctors/{fake_id}/verify?verified_by={admin_id}", json={}
    )

    assert response.status_code == 404
