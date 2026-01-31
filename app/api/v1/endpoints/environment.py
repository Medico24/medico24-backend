from fastapi import APIRouter, Query, status

from app.dependencies import CacheManagerDep
from app.schemas.environment import EnvironmentalConditionsResponse
from app.services.environment_service import EnvironmentService

router = APIRouter()


@router.get(
    "/conditions",
    response_model=EnvironmentalConditionsResponse,
    status_code=status.HTTP_200_OK,
    tags=["Environment"],
    summary="Get AQI and Weather by coordinates",
)
async def get_environmental_conditions(
    cache_manager: CacheManagerDep,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
) -> EnvironmentalConditionsResponse:
    """
    Fetch real-time Air Quality and Temperature for a specific location.

    Useful for Medico24 patient health monitoring (e.g., respiratory warnings).

    Args:
        cache_manager: Cache manager for data caching
        lat: Latitude coordinate
        lng: Longitude coordinate

    Returns:
        Environmental conditions including AQI and temperature

    Raises:
        HTTPException: If environmental data is unavailable
    """
    service = EnvironmentService(cache_manager)
    return await service.get_local_conditions(lat, lng)
