"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import AppException
from app.core.firebase import initialize_firebase
from app.core.redis_client import close_redis_connection, get_redis_client
from app.database import engine
from app.middleware.error_handler import (
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.middleware.logging import LoggingMiddleware, configure_logging

# Configure logging
configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("application_startup", environment=settings.environment)

    # Initialize Firebase Admin SDK
    try:
        initialize_firebase(settings.firebase_credentials_path or None)
        logger.info("firebase_initialized")
    except Exception as e:
        logger.warning(
            "firebase_initialization_failed",
            error=str(e),
            note="Firebase auth will not work. Set FIREBASE_CREDENTIALS_PATH env var.",
        )

    # Test database connection
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))

    # Test Redis connection
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))

    yield

    # Shutdown
    logger.info("application_shutdown")

    # Close database connections
    await engine.dispose()
    logger.info("database_connections_closed")

    # Close Redis connection
    close_redis_connection()
    logger.info("redis_connection_closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise-grade FastAPI backend for healthcare appointment management",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add exception handlers
app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, general_exception_handler)  # type: ignore[arg-type]

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Setup Prometheus instrumentation
Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/docs", "/redoc", "/openapi.json"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
