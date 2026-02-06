"""Doctor-Clinic junction table for many-to-many relationship."""

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

doctor_clinics = Table(
    "doctor_clinics",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    # Foreign Keys
    Column(
        "doctor_id",
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column(
        "clinic_id",
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    # Association Details
    Column("is_primary", Boolean, nullable=False, server_default=text("false")),
    Column("start_date", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("end_date", DateTime(timezone=True)),  # NULL = currently active
    # Clinic-specific Settings
    Column("consultation_fee", Numeric(10, 2)),  # Override doctor's default fee
    Column("consultation_duration_minutes", Integer),  # Override default (e.g., 30)
    Column("department", String(200)),  # Department within the clinic
    Column("designation", String(200)),  # Consultant, Senior Consultant, HOD, Visiting Doctor
    # Availability at this Clinic
    Column("available_days", JSON),
    # Example: ["monday", "wednesday", "friday"]
    Column("available_time_slots", JSON),
    # Example: [{"day": "monday", "slots": [{"start": "09:00", "end": "13:00"}, {"start": "15:00", "end": "18:00"}]}]
    Column("appointment_booking_enabled", Boolean, nullable=False, server_default=text("true")),
    # Statistics (Denormalized for performance)
    Column("total_appointments", Integer, nullable=False, server_default=text("0")),
    Column("completed_appointments", Integer, nullable=False, server_default=text("0")),
    Column("rating_at_clinic", Numeric(3, 2)),  # Clinic-specific rating (0.00-5.00)
    Column("rating_count_at_clinic", Integer, nullable=False, server_default=text("0")),
    # Status
    Column("status", String(20), nullable=False, server_default=text("'active'"), index=True),
    # active, on_leave, temporarily_unavailable, inactive
    # Metadata
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    ),
    # Constraints
    CheckConstraint(
        "status IN ('active', 'on_leave', 'temporarily_unavailable', 'inactive')",
        name="doctor_clinics_status_check",
    ),
)

# Composite indexes for common queries
Index("idx_doctor_clinics_doctor_id", doctor_clinics.c.doctor_id)
Index("idx_doctor_clinics_clinic_id", doctor_clinics.c.clinic_id)
Index("idx_doctor_clinics_status", doctor_clinics.c.status)
Index("idx_doctor_clinics_is_primary", doctor_clinics.c.is_primary)
Index("idx_doctor_clinics_doctor_status", doctor_clinics.c.doctor_id, doctor_clinics.c.status)
Index("idx_doctor_clinics_clinic_status", doctor_clinics.c.clinic_id, doctor_clinics.c.status)
Index(
    "idx_doctor_clinics_active",
    doctor_clinics.c.doctor_id,
    doctor_clinics.c.clinic_id,
    postgresql_where=text("end_date IS NULL AND status = 'active'"),
)
