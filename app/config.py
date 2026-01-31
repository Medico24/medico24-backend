"""Application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_parse_none_str="null",
    )

    # Application
    app_name: str = Field(default="Medico24 API", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = Field(default=False, alias="RELOAD")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_host: str = Field(..., alias="REDIS_HOST")
    redis_port: int = Field(..., alias="REDIS_PORT")
    redis_username: str = Field(default="default", alias="REDIS_USERNAME")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_decode_responses: bool = Field(default=True, alias="REDIS_DECODE_RESPONSES")

    # JWT
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    # Refresh token valid for 1 year
    refresh_token_expire_days: int = Field(default=365, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Google OAuth
    google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., alias="GOOGLE_REDIRECT_URI")
    google_maps_api_key: str = Field(default="", alias="GOOGLE_MAPS_API_KEY")

    # Firebase
    firebase_credentials_path: str | None = Field(
        default=None,
        alias="FIREBASE_CREDENTIALS_PATH",
        description="Path to Firebase service account JSON file",
    )

    firebase_config_json: str | None = Field(
        default=None,
        alias="FIREBASE_CONFIG_JSON",
        description="Raw JSON string of the Firebase service account",
    )

    # Admin Notification Secret
    admin_notification_secret: str = Field(
        default="test-admin-secret-for-development-only",
        alias="ADMIN_NOTIFICATION_SECRET",
        description="Secret key for admin notification endpoint",
    )

    # CORS
    cors_origins_str: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins_str, str):
            return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]
        return [self.cors_origins_str]

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]


# Global settings instance
settings = get_settings()
