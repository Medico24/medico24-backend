"""Clinic model definition using SQLAlchemy Core."""

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

clinics = Table(
    "clinics",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    # Basic Information
    Column("name", String(255), nullable=False, index=True),
    Column("slug", String(255), unique=True, index=True),  # URL-friendly identifier
    Column("description", Text),
    Column("logo_url", Text),
    # Contact Information (JSON for flexibility)
    Column("contacts", JSON),
    # Example: {"email": "clinic@example.com", "phone_primary": "+91...", "phone_secondary": "...", "website": "https://..."}
    # Address (simplified to essential fields)
    Column("address", Text, nullable=False),  # Full address as text
    Column("latitude", Numeric(10, 8)),
    Column("longitude", Numeric(11, 8)),
    # Opening Hours
    Column("opening_hours", JSON),
    # Example: {"monday": {"open": "09:00", "close": "18:00"}, "tuesday": {...}, "sunday": null}
    # Ratings
    Column("rating", Numeric(3, 2)),  # Average rating 0.00-5.00
    Column("rating_count", Integer, nullable=False, server_default=text("0")),
    # Status
    Column("status", String(20), nullable=False, server_default=text("'active'"), index=True),
    # active, inactive, temporarily_closed, permanently_closed
    Column("is_active", Boolean, nullable=False, server_default=text("true"), index=True),
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
    Column("deleted_at", DateTime(timezone=True)),  # Soft delete
    # Constraints
    CheckConstraint(
        "status IN ('active', 'inactive', 'temporarily_closed', 'permanently_closed')",
        name="clinics_status_check",
    ),
)

# Indexes for performance
Index("idx_clinics_status", clinics.c.status)
Index("idx_clinics_is_active", clinics.c.is_active)
Index(
    "idx_clinics_name_trgm",
    clinics.c.name,
    postgresql_using="gin",
    postgresql_ops={"name": "gin_trgm_ops"},
)
# Note: The trigram index requires pg_trgm extension, add in migration
