"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CacheManager, get_redis_client
from app.database import get_db
from app.schemas.auth import GoogleAuthRequest, LoginResponse, TokenRefresh, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/firebase/verify",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Firebase ID token verification",
)
async def firebase_verify(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: any = Depends(get_redis_client),
) -> LoginResponse:
    """
    Verify Firebase ID token from Flutter app and return JWT tokens.

    This endpoint is for mobile apps using Firebase Authentication.
    The Flutter app sends a Firebase ID token after successful Google Sign-In,
    and this endpoint verifies it, creates/updates the user, and returns
    JWT tokens for API access.

    Args:
        request: Firebase ID token from Flutter app
        db: Database session
        redis_client: Redis client for caching

    Returns:
        Access token, refresh token, and user information

    Raises:
        HTTPException: If token verification fails
    """
    cache_manager = CacheManager(redis_client)
    auth_service = AuthService(cache_manager)

    try:
        # Verify Firebase ID token
        firebase_token_data = await auth_service.verify_firebase_id_token(request.id_token)

        # Handle login (create/get user and generate tokens)
        user, tokens = await auth_service.handle_firebase_login(firebase_token_data, db)

        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            user=UserResponse(
                id=str(user["id"]),
                email=user["email"],
                name=user["full_name"] or user["email"],
                picture=user["photo_url"],
                is_active=user["is_active"],
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {e!s}",
        )


@router.post(
    "/refresh",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Refresh access token",
)
async def refresh_token(
    request: TokenRefresh,
    redis_client: any = Depends(get_redis_client),
) -> dict[str, str]:
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token
        redis_client: Redis client for caching

    Returns:
        New access token and refresh token

    Raises:
        HTTPException: If refresh token is invalid
    """
    cache_manager = CacheManager(redis_client)
    auth_service = AuthService(cache_manager)

    try:
        tokens = auth_service.refresh_access_token(request.refresh_token)

        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not refresh token: {e!s}",
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Authentication"],
    summary="Logout and revoke tokens",
)
async def logout(
    request: TokenRefresh,
    redis_client: any = Depends(get_redis_client),
) -> None:
    """
    Logout user by revoking refresh token.

    Args:
        request: Refresh token to revoke
        redis_client: Redis client for caching
    """
    cache_manager = CacheManager(redis_client)
    auth_service = AuthService(cache_manager)

    auth_service.revoke_token(request.refresh_token)
