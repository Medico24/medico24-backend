"""FastAPI dependencies."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CacheManager, get_redis_client
from app.core.security import decode_access_token
from app.database import get_db
from app.services.user_service import UserService

# Security
security = HTTPBearer()


def get_cache_manager() -> CacheManager:
    """
    Get CacheManager instance.

    Returns:
        CacheManager instance
    """
    redis_client = get_redis_client()
    return CacheManager(redis_client)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UUID:
    """
    Extract and validate user ID from JWT token.

    Args:
        credentials: Bearer token credentials

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if user_id_str is None or not isinstance(user_id_str, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    cache_manager: Annotated[CacheManager, Depends(get_cache_manager)],
) -> dict:
    """
    Get current user from database.

    Args:
        user_id: User ID from JWT token
        db: Database session
        cache_manager: Cache manager for user data

    Returns:
        User data from database

    Raises:
        HTTPException: If user not found or inactive
    """
    user_service = UserService(cache_manager)
    user = await user_service.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


# Type aliases for dependency injection
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
CacheManagerDep = Annotated[CacheManager, Depends(get_cache_manager)]
RedisClient = Annotated[Any, Depends(get_redis_client)]
