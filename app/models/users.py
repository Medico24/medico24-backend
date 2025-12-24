"""User model definition using SQLAlchemy Core."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

users = Table(
    "users",
    metadata,
    # Internal ID (for joins & performance)
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    # Firebase identity (SOURCE OF TRUTH)
    Column("firebase_uid", Text, nullable=False, unique=True, index=True),
    # Auth-related info (mirrored from Firebase)
    Column("email", Text, nullable=False, index=True),
    Column("email_verified", Boolean, nullable=False, server_default=text("false")),
    Column("auth_provider", Text, nullable=False, server_default=text("'google'")),
    # Profile info (mutable)
    Column("full_name", Text),
    Column("given_name", Text),
    Column("family_name", Text),
    Column("photo_url", Text),
    # App-specific fields (Firebase does NOT handle these)
    Column("phone", String(20)),
    Column("role", Text, nullable=False, server_default=text("'patient'")),
    # Account state
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("is_onboarded", Boolean, nullable=False, server_default=text("false")),
    # Audit
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("last_login_at", DateTime(timezone=True)),
)
