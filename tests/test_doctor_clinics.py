"""Tests for doctor_clinics junction table operations."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import and_, delete, insert, select, update

from app.models.clinics import clinics
from app.models.doctor_clinics import doctor_clinics
from app.models.doctors import doctors


@pytest.fixture
async def test_doctor(db_session):
    """Create a test doctor."""
    # Create doctor directly (no user needed)
    doctor_data = {
        "email": "doctor@test.com",
        "full_name": "Dr. Test Doctor",
        "phone": "+919876543210",
        "license_number": "DOC123456",
        "specialization": "Cardiology",
        "consultation_fee": 1000.00,
        "is_verified": True,
    }
    result = await db_session.execute(insert(doctors).values(**doctor_data).returning(doctors.c.id))
    await db_session.commit()

    return result.scalar_one()


@pytest.fixture
async def test_clinic(db_session):
    """Create a test clinic."""
    clinic_data = {
        "name": "Test Hospital",
        "slug": "test-hospital",
        "address": "123 Test Street, Mumbai",
        "contacts": {"phone_primary": "+919876543210"},
        "is_active": True,
    }
    result = await db_session.execute(insert(clinics).values(**clinic_data).returning(clinics.c.id))
    await db_session.commit()

    return result.scalar_one()


@pytest.mark.asyncio
async def test_create_doctor_clinic_association(db_session, test_doctor, test_clinic):
    """Test creating a doctor-clinic association."""
    association_data = {
        "doctor_id": test_doctor,
        "clinic_id": test_clinic,
        "is_primary": True,
        "consultation_fee": 1200.00,
        "consultation_duration_minutes": 30,
        "department": "Cardiology",
        "designation": "Senior Consultant",
        "available_days": ["monday", "wednesday", "friday"],
        "available_time_slots": [
            {
                "day": "monday",
                "slots": [{"start": "09:00", "end": "13:00"}, {"start": "15:00", "end": "18:00"}],
            }
        ],
        "status": "active",
    }

    result = await db_session.execute(
        insert(doctor_clinics).values(**association_data).returning(doctor_clinics)
    )
    await db_session.commit()

    association = result.fetchone()
    assert association is not None
    assert association.doctor_id == test_doctor
    assert association.clinic_id == test_clinic
    assert association.is_primary is True
    assert float(association.consultation_fee) == 1200.00
    assert association.department == "Cardiology"
    assert association.status == "active"


@pytest.mark.asyncio
async def test_unique_active_association(db_session, test_doctor, test_clinic):
    """Test that only one active association per doctor-clinic pair is allowed."""
    association_data = {"doctor_id": test_doctor, "clinic_id": test_clinic, "status": "active"}

    # Create first association
    await db_session.execute(insert(doctor_clinics).values(**association_data))
    await db_session.commit()

    from sqlalchemy.exc import IntegrityError

    # Try to create duplicate active association
    await db_session.execute(insert(doctor_clinics).values(**association_data))
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_multiple_clinics_for_doctor(db_session, test_doctor):
    """Test that a doctor can be associated with multiple clinics."""
    # Create two clinics
    clinic1_result = await db_session.execute(
        insert(clinics)
        .values(
            name="Clinic 1",
            slug="clinic-1",
            address="Address 1",
            contacts={"phone_primary": "+919876543210"},
        )
        .returning(clinics.c.id)
    )
    clinic1_id = clinic1_result.scalar_one()

    clinic2_result = await db_session.execute(
        insert(clinics)
        .values(
            name="Clinic 2",
            slug="clinic-2",
            address="Address 2",
            contacts={"phone_primary": "+919876543211"},
        )
        .returning(clinics.c.id)
    )
    clinic2_id = clinic2_result.scalar_one()
    await db_session.commit()

    # Associate doctor with both clinics
    await db_session.execute(
        insert(doctor_clinics).values(
            doctor_id=test_doctor, clinic_id=clinic1_id, is_primary=True, consultation_fee=1000.00
        )
    )
    await db_session.execute(
        insert(doctor_clinics).values(
            doctor_id=test_doctor, clinic_id=clinic2_id, is_primary=False, consultation_fee=1500.00
        )
    )
    await db_session.commit()

    # Verify associations
    result = await db_session.execute(
        select(doctor_clinics).where(doctor_clinics.c.doctor_id == test_doctor)
    )
    associations = result.fetchall()

    assert len(associations) == 2
    assert sum(1 for a in associations if a.is_primary) == 1  # Only one primary


@pytest.mark.asyncio
async def test_multiple_doctors_at_clinic(db_session, test_clinic):
    """Test that a clinic can have multiple doctors."""
    # Create two doctors
    doctor1_result = await db_session.execute(
        insert(doctors)
        .values(
            email="doctor1@test.com",
            full_name="Dr. Cardiologist",
            license_number="DOC001",
            specialization="Cardiology",
        )
        .returning(doctors.c.id)
    )
    doctor1_id = doctor1_result.scalar_one()

    doctor2_result = await db_session.execute(
        insert(doctors)
        .values(
            email="doctor2@test.com",
            full_name="Dr. Neurologist",
            license_number="DOC002",
            specialization="Neurology",
        )
        .returning(doctors.c.id)
    )
    doctor2_id = doctor2_result.scalar_one()
    await db_session.commit()

    # Associate both doctors with clinic
    await db_session.execute(
        insert(doctor_clinics).values(
            doctor_id=doctor1_id, clinic_id=test_clinic, department="Cardiology"
        )
    )
    await db_session.execute(
        insert(doctor_clinics).values(
            doctor_id=doctor2_id, clinic_id=test_clinic, department="Neurology"
        )
    )
    await db_session.commit()

    # Verify associations
    result = await db_session.execute(
        select(doctor_clinics).where(doctor_clinics.c.clinic_id == test_clinic)
    )
    associations = result.fetchall()

    assert len(associations) == 2


@pytest.mark.asyncio
async def test_update_association_status(db_session, test_doctor, test_clinic):
    """Test updating association status."""
    # Create association
    result = await db_session.execute(
        insert(doctor_clinics)
        .values(doctor_id=test_doctor, clinic_id=test_clinic, status="active")
        .returning(doctor_clinics.c.id)
    )
    association_id = result.scalar_one()
    await db_session.commit()

    # Update to on_leave
    await db_session.execute(
        update(doctor_clinics)
        .where(doctor_clinics.c.id == association_id)
        .values(status="on_leave")
    )
    await db_session.commit()

    # Verify update
    result = await db_session.execute(
        select(doctor_clinics).where(doctor_clinics.c.id == association_id)
    )
    updated = result.fetchone()

    assert updated.status == "on_leave"


@pytest.mark.asyncio
async def test_end_association(db_session, test_doctor, test_clinic):
    """Test ending a doctor-clinic association."""
    # Create association
    result = await db_session.execute(
        insert(doctor_clinics)
        .values(doctor_id=test_doctor, clinic_id=test_clinic, status="active")
        .returning(doctor_clinics.c.id)
    )
    association_id = result.scalar_one()
    await db_session.commit()

    # End association
    end_date = datetime.now(UTC)
    await db_session.execute(
        update(doctor_clinics)
        .where(doctor_clinics.c.id == association_id)
        .values(end_date=end_date, status="inactive")
    )
    await db_session.commit()

    # Verify end_date is set
    result = await db_session.execute(
        select(doctor_clinics).where(doctor_clinics.c.id == association_id)
    )
    ended = result.fetchone()

    assert ended.end_date is not None
    assert ended.status == "inactive"


@pytest.mark.asyncio
async def test_query_active_associations(db_session, test_doctor, test_clinic):
    """Test querying only active associations."""
    # Create active association
    await db_session.execute(
        insert(doctor_clinics).values(
            doctor_id=test_doctor, clinic_id=test_clinic, status="active", end_date=None
        )
    )

    # Create ended association (need different clinic to avoid unique constraint)
    another_clinic = await db_session.execute(
        insert(clinics)
        .values(
            name="Another Clinic",
            slug="another-clinic",
            address="Another Address",
            contacts={"phone_primary": "+919876543212"},
        )
        .returning(clinics.c.id)
    )
    another_clinic_id = another_clinic.scalar_one()

    end_date = datetime.now(UTC) - timedelta(days=30)
    await db_session.execute(
        insert(doctor_clinics).values(
            doctor_id=test_doctor, clinic_id=another_clinic_id, status="inactive", end_date=end_date
        )
    )
    await db_session.commit()

    # Query only active associations
    result = await db_session.execute(
        select(doctor_clinics).where(
            and_(
                doctor_clinics.c.doctor_id == test_doctor,
                doctor_clinics.c.status == "active",
                doctor_clinics.c.end_date.is_(None),
            )
        )
    )
    active_associations = result.fetchall()

    assert len(active_associations) == 1


@pytest.mark.asyncio
async def test_cascade_delete_doctor(db_session, test_doctor, test_clinic):
    """Test that deleting a doctor cascades to associations."""
    # Create association
    await db_session.execute(
        insert(doctor_clinics).values(doctor_id=test_doctor, clinic_id=test_clinic)
    )
    await db_session.commit()

    # Delete doctor
    await db_session.execute(delete(doctors).where(doctors.c.id == test_doctor))
    await db_session.commit()

    # Verify association is also deleted
    result = await db_session.execute(
        select(doctor_clinics).where(doctor_clinics.c.doctor_id == test_doctor)
    )
    associations = result.fetchall()

    assert len(associations) == 0


@pytest.mark.asyncio
async def test_update_statistics(db_session, test_doctor, test_clinic):
    """Test updating appointment statistics."""
    # Create association
    result = await db_session.execute(
        insert(doctor_clinics)
        .values(
            doctor_id=test_doctor,
            clinic_id=test_clinic,
            total_appointments=0,
            completed_appointments=0,
        )
        .returning(doctor_clinics.c.id)
    )
    association_id = result.scalar_one()
    await db_session.commit()

    # Update statistics
    await db_session.execute(
        update(doctor_clinics)
        .where(doctor_clinics.c.id == association_id)
        .values(
            total_appointments=50,
            completed_appointments=45,
            rating_at_clinic=4.7,
            rating_count_at_clinic=40,
        )
    )
    await db_session.commit()

    # Verify statistics
    result = await db_session.execute(
        select(doctor_clinics).where(doctor_clinics.c.id == association_id)
    )
    updated = result.fetchone()

    assert updated.total_appointments == 50
    assert updated.completed_appointments == 45
    assert float(updated.rating_at_clinic) == 4.7
    assert updated.rating_count_at_clinic == 40
