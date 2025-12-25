"""Health check endpoints."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config import settings
from app.core.redis_client import check_redis_connection
from app.database import check_database_connection

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""

    status: str
    version: str
    environment: str
    database: str
    redis: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Basic health check",
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        Basic health status
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Detailed health check",
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check with database and Redis status.

    Returns:
        Detailed health status including dependencies
    """
    db_healthy = await check_database_connection()
    redis_healthy = await check_redis_connection()

    return DetailedHealthResponse(
        status="healthy" if db_healthy and redis_healthy else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        database="healthy" if db_healthy else "unhealthy",
        redis="healthy" if redis_healthy else "unhealthy",
    )


@router.get(
    "/ping",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Simple ping",
)
async def ping() -> dict[str, str]:
    """
    Simple ping endpoint.

    Returns:
        Pong response
    """
    return {"message": "pong"}
