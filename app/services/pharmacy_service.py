"""Pharmacy service for business logic."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pharmacies import pharmacies, pharmacy_hours, pharmacy_locations
from app.schemas.pharmacies import (
    PharmacyCreate,
    PharmacyHoursCreate,
    PharmacyLocationUpdate,
    PharmacyUpdate,
)


class PharmacyService:
    """Service for pharmacy operations."""

    @staticmethod
    async def create_pharmacy(db: AsyncSession, pharmacy_data: PharmacyCreate) -> dict:
        """Create a new pharmacy with location and hours."""
        # Create pharmacy
        pharmacy_query = (
            pharmacies.insert()
            .values(
                name=pharmacy_data.name,
                description=pharmacy_data.description,
                phone=pharmacy_data.phone,
                email=pharmacy_data.email,
                supports_delivery=pharmacy_data.supports_delivery,
                supports_pickup=pharmacy_data.supports_pickup,
            )
            .returning(pharmacies)
        )

        result = await db.execute(pharmacy_query)
        pharmacy = result.mappings().first()

        if not pharmacy:
            raise ValueError("Failed to create pharmacy")

        pharmacy_id = pharmacy["id"]

        # Create location
        location_query = (
            pharmacy_locations.insert()
            .values(
                pharmacy_id=pharmacy_id,
                address_line=pharmacy_data.location.address_line,
                city=pharmacy_data.location.city,
                state=pharmacy_data.location.state,
                country=pharmacy_data.location.country,
                pincode=pharmacy_data.location.pincode,
                latitude=pharmacy_data.location.latitude,
                longitude=pharmacy_data.location.longitude,
            )
            .returning(pharmacy_locations)
        )

        await db.execute(location_query)

        # Update geo column using PostGIS
        await db.execute(
            text(
                """
                UPDATE pharmacy_locations
                SET geo = ST_MakePoint(:longitude, :latitude)
                WHERE pharmacy_id = :pharmacy_id
                """
            ),
            {
                "longitude": pharmacy_data.location.longitude,
                "latitude": pharmacy_data.location.latitude,
                "pharmacy_id": pharmacy_id,
            },
        )

        # Create hours if provided
        if pharmacy_data.hours:
            hours_values = [
                {
                    "pharmacy_id": pharmacy_id,
                    "day_of_week": hour.day_of_week,
                    "open_time": hour.open_time,
                    "close_time": hour.close_time,
                    "is_closed": hour.is_closed,
                }
                for hour in pharmacy_data.hours
            ]
            await db.execute(pharmacy_hours.insert().values(hours_values))

        await db.commit()

        # Return complete pharmacy data
        result = await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)
        if not result:
            raise ValueError("Failed to retrieve created pharmacy")
        return result

    @staticmethod
    async def get_pharmacy_by_id(db: AsyncSession, pharmacy_id: UUID) -> dict | None:
        """Get pharmacy by ID with location and hours."""
        # Get pharmacy
        pharmacy_query = select(pharmacies).where(pharmacies.c.id == pharmacy_id)
        result = await db.execute(pharmacy_query)
        pharmacy = result.mappings().first()

        if not pharmacy:
            return None

        pharmacy_dict = dict(pharmacy)

        # Get location
        location_query = select(pharmacy_locations).where(
            pharmacy_locations.c.pharmacy_id == pharmacy_id
        )
        result = await db.execute(location_query)
        location = result.mappings().first()
        pharmacy_dict["location"] = dict(location) if location else None

        # Get hours
        hours_query = (
            select(pharmacy_hours)
            .where(pharmacy_hours.c.pharmacy_id == pharmacy_id)
            .order_by(pharmacy_hours.c.day_of_week)
        )
        result = await db.execute(hours_query)
        pharmacy_dict["hours"] = [dict(row) for row in result.mappings().all()]

        return pharmacy_dict

    @staticmethod
    async def get_pharmacies(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        is_active: bool = True,
        is_verified: bool | None = None,
        supports_delivery: bool | None = None,
        supports_pickup: bool | None = None,
    ) -> list[dict]:
        """Get list of pharmacies with filtering."""
        conditions = [pharmacies.c.is_active == is_active]

        if is_verified is not None:
            conditions.append(pharmacies.c.is_verified == is_verified)
        if supports_delivery is not None:
            conditions.append(pharmacies.c.supports_delivery == supports_delivery)
        if supports_pickup is not None:
            conditions.append(pharmacies.c.supports_pickup == supports_pickup)

        query = (
            select(pharmacies)
            .where(and_(*conditions))
            .offset(skip)
            .limit(limit)
            .order_by(pharmacies.c.rating.desc(), pharmacies.c.created_at.desc())
        )

        result = await db.execute(query)
        pharmacy_list = [dict(row) for row in result.mappings().all()]

        # Get locations for each pharmacy
        for pharmacy in pharmacy_list:
            location_query = select(pharmacy_locations).where(
                pharmacy_locations.c.pharmacy_id == pharmacy["id"]
            )
            location_result = await db.execute(location_query)
            location = location_result.mappings().first()
            pharmacy["location"] = dict(location) if location else None

        return pharmacy_list

    @staticmethod
    async def search_pharmacies_nearby(
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        skip: int = 0,
        limit: int = 20,
        is_active: bool = True,
        is_verified: bool | None = None,
        supports_delivery: bool | None = None,
        supports_pickup: bool | None = None,
    ) -> list[dict]:
        """Search pharmacies within a radius using PostGIS."""
        conditions = [pharmacies.c.is_active == is_active]

        if is_verified is not None:
            conditions.append(pharmacies.c.is_verified == is_verified)
        if supports_delivery is not None:
            conditions.append(pharmacies.c.supports_delivery == supports_delivery)
        if supports_pickup is not None:
            conditions.append(pharmacies.c.supports_pickup == supports_pickup)

        # Use PostGIS for geographic search
        query_text = text(
            """
            SELECT
                p.*,
                pl.id as location_id,
                pl.address_line,
                pl.city,
                pl.state,
                pl.country,
                pl.pincode,
                pl.latitude,
                pl.longitude,
                pl.created_at as location_created_at,
                ST_Distance(
                    pl.geo::geography,
                    ST_MakePoint(:longitude, :latitude)::geography
                ) / 1000 as distance_km
            FROM pharmacies p
            INNER JOIN pharmacy_locations pl ON p.id = pl.pharmacy_id
            WHERE
                ST_DWithin(
                    pl.geo::geography,
                    ST_MakePoint(:longitude, :latitude)::geography,
                    :radius_m
                )
                AND p.is_active = :is_active
                {is_verified_condition}
                {supports_delivery_condition}
                {supports_pickup_condition}
            ORDER BY distance_km ASC
            LIMIT :limit OFFSET :skip
            """
        )

        # Build dynamic conditions
        is_verified_condition = ""
        if is_verified is not None:
            is_verified_condition = f"AND p.is_verified = {is_verified}"

        supports_delivery_condition = ""
        if supports_delivery is not None:
            supports_delivery_condition = f"AND p.supports_delivery = {supports_delivery}"

        supports_pickup_condition = ""
        if supports_pickup is not None:
            supports_pickup_condition = f"AND p.supports_pickup = {supports_pickup}"

        query_text = text(
            query_text.text.format(
                is_verified_condition=is_verified_condition,
                supports_delivery_condition=supports_delivery_condition,
                supports_pickup_condition=supports_pickup_condition,
            )
        )

        result = await db.execute(
            query_text,
            {
                "latitude": latitude,
                "longitude": longitude,
                "radius_m": radius_km * 1000,  # Convert km to meters
                "is_active": is_active,
                "skip": skip,
                "limit": limit,
            },
        )

        rows = result.mappings().all()
        pharmacy_list = []

        for row in rows:
            pharmacy = {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "phone": row["phone"],
                "email": row["email"],
                "is_verified": row["is_verified"],
                "is_active": row["is_active"],
                "rating": row["rating"],
                "rating_count": row["rating_count"],
                "supports_delivery": row["supports_delivery"],
                "supports_pickup": row["supports_pickup"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "distance_km": float(row["distance_km"]),
                "location": {
                    "id": row["location_id"],
                    "pharmacy_id": row["id"],
                    "address_line": row["address_line"],
                    "city": row["city"],
                    "state": row["state"],
                    "country": row["country"],
                    "pincode": row["pincode"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "created_at": row["location_created_at"],
                },
            }
            pharmacy_list.append(pharmacy)

        return pharmacy_list

    @staticmethod
    async def update_pharmacy(
        db: AsyncSession, pharmacy_id: UUID, pharmacy_data: PharmacyUpdate
    ) -> dict | None:
        """Update pharmacy information."""
        # Build update values
        update_values = {}
        if pharmacy_data.name is not None:
            update_values["name"] = pharmacy_data.name
        if pharmacy_data.description is not None:
            update_values["description"] = pharmacy_data.description
        if pharmacy_data.phone is not None:
            update_values["phone"] = pharmacy_data.phone
        if pharmacy_data.email is not None:
            update_values["email"] = pharmacy_data.email
        if pharmacy_data.supports_delivery is not None:
            update_values["supports_delivery"] = pharmacy_data.supports_delivery
        if pharmacy_data.supports_pickup is not None:
            update_values["supports_pickup"] = pharmacy_data.supports_pickup
        if pharmacy_data.is_active is not None:
            update_values["is_active"] = pharmacy_data.is_active

        if not update_values:
            return await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)

        update_values["updated_at"] = datetime.now(UTC)

        query = (
            update(pharmacies)
            .where(pharmacies.c.id == pharmacy_id)
            .values(**update_values)
            .returning(pharmacies)
        )

        result = await db.execute(query)
        await db.commit()

        updated = result.mappings().first()
        if not updated:
            return None

        return await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)

    @staticmethod
    async def delete_pharmacy(db: AsyncSession, pharmacy_id: UUID) -> bool:
        """Delete a pharmacy (cascades to locations and hours)."""
        query = delete(pharmacies).where(pharmacies.c.id == pharmacy_id)
        result = await db.execute(query)
        await db.commit()
        # Check if any rows were deleted
        return result.rowcount > 0  # type: ignore[attr-defined]

    @staticmethod
    def _build_location_update_values(
        location_data: PharmacyLocationUpdate,
    ) -> dict:
        """Build update values from location data, excluding None values."""
        fields = [
            "address_line",
            "city",
            "state",
            "country",
            "pincode",
            "latitude",
            "longitude",
        ]
        return {
            field: getattr(location_data, field)
            for field in fields
            if getattr(location_data, field) is not None
        }

    @staticmethod
    async def _update_geo_column(
        db: AsyncSession, pharmacy_id: UUID, location_data: PharmacyLocationUpdate
    ) -> None:
        """Update geo column if latitude or longitude changed."""
        if location_data.latitude is None and location_data.longitude is None:
            return

        # Get current location to get coordinates
        location_select = select(pharmacy_locations).where(
            pharmacy_locations.c.pharmacy_id == pharmacy_id
        )
        loc_result = await db.execute(location_select)
        location = loc_result.mappings().first()

        if location:
            await db.execute(
                text(
                    """
                    UPDATE pharmacy_locations
                    SET geo = ST_MakePoint(:longitude, :latitude)
                    WHERE pharmacy_id = :pharmacy_id
                    """
                ),
                {
                    "longitude": location["longitude"],
                    "latitude": location["latitude"],
                    "pharmacy_id": pharmacy_id,
                },
            )

    @staticmethod
    async def update_pharmacy_location(
        db: AsyncSession, pharmacy_id: UUID, location_data: PharmacyLocationUpdate
    ) -> dict | None:
        """Update pharmacy location."""
        update_values = PharmacyService._build_location_update_values(location_data)

        if not update_values:
            return await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)

        query = (
            update(pharmacy_locations)
            .where(pharmacy_locations.c.pharmacy_id == pharmacy_id)
            .values(**update_values)
            .returning(pharmacy_locations)
        )

        await db.execute(query)
        await PharmacyService._update_geo_column(db, pharmacy_id, location_data)
        await db.commit()

        return await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)

    @staticmethod
    async def add_pharmacy_hours(
        db: AsyncSession, pharmacy_id: UUID, hours_data: PharmacyHoursCreate
    ) -> dict | None:
        """Add or update pharmacy hours for a specific day."""
        # Check if hours already exist for this day
        existing_query = select(pharmacy_hours).where(
            and_(
                pharmacy_hours.c.pharmacy_id == pharmacy_id,
                pharmacy_hours.c.day_of_week == hours_data.day_of_week,
            )
        )
        result = await db.execute(existing_query)
        existing = result.mappings().first()

        if existing:
            # Update existing
            query = (
                update(pharmacy_hours)
                .where(pharmacy_hours.c.id == existing["id"])
                .values(
                    open_time=hours_data.open_time,
                    close_time=hours_data.close_time,
                    is_closed=hours_data.is_closed,
                )
                .returning(pharmacy_hours)
            )
        else:
            # Insert new
            query = (
                pharmacy_hours.insert()
                .values(
                    pharmacy_id=pharmacy_id,
                    day_of_week=hours_data.day_of_week,
                    open_time=hours_data.open_time,
                    close_time=hours_data.close_time,
                    is_closed=hours_data.is_closed,
                )
                .returning(pharmacy_hours)
            )

        result = await db.execute(query)
        await db.commit()

        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    async def get_pharmacy_hours(db: AsyncSession, pharmacy_id: UUID) -> list[dict]:
        """Get all hours for a pharmacy."""
        query = (
            select(pharmacy_hours)
            .where(pharmacy_hours.c.pharmacy_id == pharmacy_id)
            .order_by(pharmacy_hours.c.day_of_week)
        )

        result = await db.execute(query)
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def delete_pharmacy_hours(db: AsyncSession, pharmacy_id: UUID, day_of_week: int) -> bool:
        """Delete pharmacy hours for a specific day."""
        query = delete(pharmacy_hours).where(
            and_(
                pharmacy_hours.c.pharmacy_id == pharmacy_id,
                pharmacy_hours.c.day_of_week == day_of_week,
            )
        )
        result = await db.execute(query)
        await db.commit()
        # Check if any rows were deleted
        return result.rowcount > 0  # type: ignore[attr-defined]
