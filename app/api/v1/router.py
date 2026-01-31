"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    appointments,
    auth,
    environment,
    health,
    notifications,
    pharmacies,
    users,
)

api_router = APIRouter()

# Include routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(environment.router, prefix="/environment", tags=["Environment"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(pharmacies.router, tags=["Pharmacies"])
api_router.include_router(notifications.router, tags=["Notifications"])
api_router.include_router(admin.router, tags=["Admin"])
