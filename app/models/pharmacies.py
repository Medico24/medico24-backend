"""Pharmacy models definition using SQLAlchemy Core."""

from sqlalchemy import (
    Boolean,
    Column,
    Double,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    Table,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

metadata = MetaData()

# Pharmacies table
pharmacies = Table(
    "pharmacies",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=True),
    Column("phone", Text, nullable=True),
    Column("email", Text, nullable=True),
    Column("is_verified", Boolean, nullable=False, server_default=text("false")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("rating", Numeric(precision=2, scale=1), nullable=True, server_default=text("0.0")),
    Column("rating_count", Integer, nullable=True, server_default=text("0")),
    Column("supports_delivery", Boolean, nullable=False, server_default=text("false")),
    Column("supports_pickup", Boolean, nullable=False, server_default=text("true")),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    ),
    Column(
        "updated_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    ),
)

# Pharmacy locations table
pharmacy_locations = Table(
    "pharmacy_locations",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "pharmacy_id",
        UUID(as_uuid=True),
        ForeignKey("pharmacies.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("address_line", Text, nullable=False),
    Column("city", Text, nullable=False),
    Column("state", Text, nullable=True),
    Column("country", Text, nullable=False, server_default=text("'India'")),
    Column("pincode", Text, nullable=True),
    Column("latitude", Double, nullable=False),
    Column("longitude", Double, nullable=False),
    # Note: The geo column (Geography type) is added via migration
    # as it requires PostGIS and is not directly supported by SQLAlchemy Core
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    ),
)

# Pharmacy hours table
pharmacy_hours = Table(
    "pharmacy_hours",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column(
        "pharmacy_id",
        UUID(as_uuid=True),
        ForeignKey("pharmacies.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("day_of_week", SmallInteger, nullable=False),  # 1=Monday, 7=Sunday
    Column("open_time", Time, nullable=False),
    Column("close_time", Time, nullable=False),
    Column("is_closed", Boolean, nullable=False, server_default=text("false")),
    UniqueConstraint("pharmacy_id", "day_of_week", name="unique_day_per_pharmacy"),
)
