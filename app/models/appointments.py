"""Appointments table model using SQLAlchemy Core."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    MetaData,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, VARCHAR

# Metadata for all tables
metadata = MetaData()

# Appointments table
appointments = Table(
    "appointments",
    metadata,
    Column(
        "id",
        UUID,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    # Ownership / references
    Column("patient_id", UUID, nullable=False, index=True),
    Column(
        "doctor_id", UUID, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, index=True
    ),
    Column(
        "clinic_id", UUID, ForeignKey("clinics.id", ondelete="SET NULL"), nullable=True, index=True
    ),
    Column(
        "doctor_clinic_id",
        UUID,
        ForeignKey("doctor_clinics.id", ondelete="SET NULL"),
        nullable=True,
    ),
    # Snapshot fields (denormalized for history/audit)
    Column("clinic_name", Text, nullable=True),
    Column("doctor_name", Text, nullable=False),
    # Appointment details
    Column("appointment_at", TIMESTAMP(timezone=True), nullable=False),
    Column("appointment_end_at", TIMESTAMP(timezone=True), nullable=True),
    Column("reason", Text, nullable=False),
    # Contact
    Column("contact_phone", VARCHAR(20), nullable=False),
    # Status management
    Column(
        "status",
        Text,
        nullable=False,
        server_default="scheduled",
    ),
    # Metadata
    Column("notes", Text, nullable=True),
    Column("source", Text, server_default="patient_app"),
    # Audit fields
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("cancelled_at", TIMESTAMP(timezone=True), nullable=True),
    # Soft delete (healthcare compliance)
    Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
    # Constraints
    CheckConstraint(
        "status IN ('scheduled', 'confirmed', 'rescheduled', 'cancelled', 'completed', 'no_show')",
        name="appointments_status_check",
    ),
)
