"""Environment service for weather and air quality logic."""

import asyncio

import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.core.redis_client import CacheManager
from app.schemas.environment import EnvironmentalConditionsResponse


class EnvironmentService:
    """Service for fetching and caching environmental data from Google APIs."""

    AQI_URL = "https://airquality.googleapis.com/v1/currentConditions:lookup"
    WEATHER_URL = "https://weather.googleapis.com/v1/currentConditions:lookup"

    # Environment data is stable for ~15-30 mins
    CACHE_TTL = 1200  # 20 minutes

    def __init__(self, cache_manager: CacheManager | None = None):
        self.cache = cache_manager

    def _get_cache_key(self, lat: float, lng: float) -> str:
        # Rounding to 3 decimal places (~110m - 500m precision)
        # improves cache hit rates for nearby users.
        return f"env:data:{round(lat, 3)}:{round(lng, 3)}"

    def _raise_api_error(self) -> None:
        """Raise an exception for API fetch failures."""
        raise ValueError("Failed to fetch data from Google Environment APIs")

    async def get_local_conditions(self, lat: float, lng: float) -> EnvironmentalConditionsResponse:
        """Fetch AQI and Temperature using Google APIs, checking cache first."""
        cache_key = self._get_cache_key(lat, lng)

        if self.cache:
            cached = self.cache.get_json(cache_key)
            if cached:
                return EnvironmentalConditionsResponse(**cached)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Concurrent calls to Google APIs
                aqi_task = client.post(
                    EnvironmentService.AQI_URL,
                    params={"key": settings.google_maps_api_key},
                    json={"location": {"latitude": lat, "longitude": lng}},
                )

                weather_task = client.get(
                    EnvironmentService.WEATHER_URL,
                    params={
                        "key": settings.google_maps_api_key,
                        "location.latitude": lat,
                        "location.longitude": lng,
                    },
                )

                aqi_res, weather_res = await asyncio.gather(aqi_task, weather_task)

                # Validate responses
                if aqi_res.status_code != 200 or weather_res.status_code != 200:
                    self._raise_api_error()

                aqi_data = aqi_res.json()
                weather_data = weather_res.json()

                env_data = {
                    "aqi": aqi_data["indexes"][0]["aqi"],
                    "aqi_category": aqi_data["indexes"][0]["category"],
                    "temperature": weather_data["temperature"]["degrees"],
                    "condition": weather_data["weatherCondition"]["description"]["text"],
                }

                if self.cache:
                    self.cache.set_json(cache_key, env_data, ttl=self.CACHE_TTL)

                return EnvironmentalConditionsResponse(**env_data)

            except Exception as e:
                # Logging here via your structlog setup would be ideal
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Environmental data currently unavailable: {e!s}",
                )
