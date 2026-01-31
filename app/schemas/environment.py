from pydantic import BaseModel, Field


class EnvironmentalConditionsResponse(BaseModel):
    """Response model for environmental conditions including AQI and weather data."""

    aqi: int = Field(..., description="The Universal Air Quality Index")
    aqi_category: str = Field(..., description="Health category (e.g., Good, Moderate)")
    temperature: float = Field(..., description="Temperature in Celsius")
    condition: str = Field(..., description="Weather description")

    class Config:
        """Pydantic configuration for the response model."""

        from_attributes = True
