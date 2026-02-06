"""Tests for clinics model and operations."""

from datetime import UTC

import pytest
from sqlalchemy import insert, select, update

from app.models.clinics import clinics


@pytest.mark.asyncio
async def test_create_clinic(db_session):
    """Test creating a clinic."""
    clinic_data = {
        "name": "City General Hospital",
        "slug": "city-general-hospital",
        "description": "A leading multi-specialty hospital",
        "logo_url": "https://example.com/logo.png",
        "contacts": {
            "email": "info@cityhospital.com",
            "phone_primary": "+919876543210",
            "phone_secondary": "+919876543211",
            "website": "https://cityhospital.com",
        },
        "address": "123 Main Street, Downtown, Mumbai, Maharashtra 400001, India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "opening_hours": {
            "monday": {"open": "08:00", "close": "20:00"},
            "tuesday": {"open": "08:00", "close": "20:00"},
            "wednesday": {"open": "08:00", "close": "20:00"},
            "thursday": {"open": "08:00", "close": "20:00"},
            "friday": {"open": "08:00", "close": "20:00"},
            "saturday": {"open": "09:00", "close": "18:00"},
            "sunday": None,
        },
        "status": "active",
        "is_active": True,
    }

    # Insert clinic
    result = await db_session.execute(insert(clinics).values(**clinic_data).returning(clinics))
    await db_session.commit()

    clinic = result.fetchone()
    assert clinic is not None
    assert clinic.name == clinic_data["name"]
    assert clinic.slug == clinic_data["slug"]
    assert clinic.contacts["email"] == "info@cityhospital.com"
    assert clinic.address == clinic_data["address"]
    assert clinic.status == "active"
    assert clinic.is_active is True
    assert clinic.id is not None


@pytest.mark.asyncio
async def test_unique_slug(db_session):
    """Test that clinic slug must be unique."""
    clinic_data = {
        "name": "Hospital A",
        "slug": "hospital-a",
        "address": "123 Street",
        "contacts": {"phone_primary": "+919876543210"},
    }

    # Insert first clinic
    await db_session.execute(insert(clinics).values(**clinic_data))
    await db_session.commit()

    # Try to insert duplicate slug
    duplicate_data = {
        "name": "Hospital B",
        "slug": "hospital-a",  # Same slug
        "address": "456 Street",
        "contacts": {"phone_primary": "+919876543211"},
    }

    from sqlalchemy.exc import IntegrityError

    await db_session.execute(insert(clinics).values(**duplicate_data))
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_clinic_status_constraint(db_session):
    """Test clinic status must be valid."""
    from sqlalchemy.exc import IntegrityError

    clinic_data = {
        "name": "Test Clinic",
        "slug": "test-clinic",
        "address": "Test Address",
        "status": "invalid_status",  # Invalid status
        "contacts": {"phone_primary": "+919876543210"},
    }

    await db_session.execute(insert(clinics).values(**clinic_data))
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_update_clinic(db_session):
    """Test updating a clinic."""
    # Create clinic
    clinic_data = {
        "name": "Old Name",
        "slug": "old-name",
        "address": "Old Address",
        "contacts": {"phone_primary": "+919876543210"},
    }

    result = await db_session.execute(insert(clinics).values(**clinic_data).returning(clinics.c.id))
    await db_session.commit()
    clinic_id = result.scalar_one()

    # Update clinic
    await db_session.execute(
        update(clinics)
        .where(clinics.c.id == clinic_id)
        .values(name="New Name", address="New Address", rating=4.5, rating_count=100)
    )
    await db_session.commit()

    # Verify update
    result = await db_session.execute(select(clinics).where(clinics.c.id == clinic_id))
    updated_clinic = result.fetchone()

    assert updated_clinic.name == "New Name"
    assert updated_clinic.address == "New Address"
    assert float(updated_clinic.rating) == 4.5
    assert updated_clinic.rating_count == 100


@pytest.mark.asyncio
async def test_soft_delete_clinic(db_session):
    """Test soft deleting a clinic."""
    from datetime import datetime

    # Create clinic
    clinic_data = {
        "name": "To Delete",
        "slug": "to-delete",
        "address": "Delete Address",
        "contacts": {"phone_primary": "+919876543210"},
    }

    result = await db_session.execute(insert(clinics).values(**clinic_data).returning(clinics.c.id))
    await db_session.commit()
    clinic_id = result.scalar_one()

    # Soft delete
    await db_session.execute(
        update(clinics).where(clinics.c.id == clinic_id).values(deleted_at=datetime.now(UTC))
    )
    await db_session.commit()

    # Verify soft delete
    result = await db_session.execute(select(clinics).where(clinics.c.id == clinic_id))
    deleted_clinic = result.fetchone()

    assert deleted_clinic.deleted_at is not None


@pytest.mark.asyncio
async def test_list_active_clinics(db_session):
    """Test listing active clinics only."""
    # Create active clinic
    await db_session.execute(
        insert(clinics).values(
            name="Active Clinic",
            slug="active-clinic",
            address="Active Address",
            status="active",
            is_active=True,
            contacts={"phone_primary": "+919876543210"},
        )
    )

    # Create inactive clinic
    await db_session.execute(
        insert(clinics).values(
            name="Inactive Clinic",
            slug="inactive-clinic",
            address="Inactive Address",
            status="inactive",
            is_active=False,
            contacts={"phone_primary": "+919876543211"},
        )
    )
    await db_session.commit()

    # Query only active clinics
    result = await db_session.execute(
        select(clinics).where(clinics.c.status == "active", clinics.c.is_active)
    )
    active_clinics = result.fetchall()

    assert len(active_clinics) == 1
    assert active_clinics[0].name == "Active Clinic"


@pytest.mark.asyncio
async def test_clinic_with_location(db_session):
    """Test clinic with geographical coordinates."""
    clinic_data = {
        "name": "Geo Clinic",
        "slug": "geo-clinic",
        "address": "Mumbai, India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "contacts": {"phone_primary": "+919876543210"},
    }

    result = await db_session.execute(insert(clinics).values(**clinic_data).returning(clinics))
    await db_session.commit()

    clinic = result.fetchone()
    assert float(clinic.latitude) == 19.0760
    assert float(clinic.longitude) == 72.8777
