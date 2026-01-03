"""Authentication service for Firebase and JWT."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.firebase import verify_firebase_token
from app.core.redis_client import CacheManager
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.schemas.auth import Token
from app.schemas.users import UserCreate
from app.services.user_service import UserService


class AuthService:
    """Authentication service for handling Firebase and JWT operations."""

    def __init__(self, cache_manager: CacheManager):
        """Initialize auth service with cache manager."""
        self.cache = cache_manager

    async def verify_firebase_id_token(self, id_token: str) -> dict:
        """
        Verify Firebase ID token and extract user information.

        Args:
            id_token: Firebase ID token from Flutter app

        Returns:
            Decoded token with user claims

        Raises:
            UnauthorizedException: If token verification fails
        """
        try:
            decoded_token = await verify_firebase_token(id_token)
            return decoded_token
        except ValueError as e:
            raise UnauthorizedException(str(e))
        except Exception as e:
            raise UnauthorizedException(f"Token verification failed: {e!s}")

    async def handle_firebase_login(
        self, firebase_token_data: dict, db: AsyncSession
    ) -> tuple[dict, Token]:
        """
        Handle Firebase login: create or get user and generate tokens.

        Args:
            firebase_token_data: Decoded Firebase token with user info
            db: Database session

        Returns:
            Tuple of (user dict, token pair)
        """
        # Extract user info from Firebase token
        firebase_uid = firebase_token_data["uid"]
        email = firebase_token_data.get("email")

        # Ensure email is not None
        if not email:
            raise UnauthorizedException("Email is required from Firebase token")

        name = firebase_token_data.get("name", email)
        picture = firebase_token_data.get("picture")
        email_verified = firebase_token_data.get("email_verified", False)

        # Parse name into given/family if available
        given_name = firebase_token_data.get("given_name")
        family_name = firebase_token_data.get("family_name")

        # If given/family name not in token, try to split full name
        if not given_name and name:
            name_parts = name.split(" ", 1)
            given_name = name_parts[0]
            family_name = name_parts[1] if len(name_parts) > 1 else None

        # Create user data
        user_data = UserCreate(
            firebase_uid=firebase_uid,
            email=email,
            email_verified=email_verified,
            full_name=name,
            given_name=given_name,
            family_name=family_name,
            photo_url=picture,
            phone=None,
            auth_provider="google",
        )

        # Get or create user using UserService with cache
        user_service = UserService(self.cache)
        user = await user_service.get_or_create_user(
            db=db,
            firebase_uid=firebase_uid,
            email=email,
            user_data=user_data,
        )

        # Create tokens using internal user ID
        tokens = self.create_tokens(str(user["id"]))

        return user, tokens

    def create_tokens(self, user_id: str) -> Token:
        """
        Create access and refresh tokens for a user.

        Args:
            user_id: User identifier (internal UUID)

        Returns:
            Token pair (access and refresh)
        """
        access_token = create_access_token(
            data={"sub": user_id},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

        refresh_token = create_refresh_token(
            data={"sub": user_id},
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    def refresh_access_token(self, refresh_token: str) -> Token:
        """
        Create new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token pair

        Raises:
            UnauthorizedException: If refresh token is invalid
        """
        payload = decode_refresh_token(refresh_token)

        if payload is None:
            raise UnauthorizedException("Invalid refresh token")

        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Invalid refresh token")

        # Check if token is blacklisted
        if self.cache.exists(f"blacklist:{refresh_token}"):
            raise UnauthorizedException("Token has been revoked")

        return self.create_tokens(user_id)

    def revoke_token(self, token: str, ttl: int = 86400 * 365) -> None:
        """
        Revoke a refresh token by adding it to blacklist.

        Args:
            token: Token to revoke
            ttl: Time to live for blacklist entry (default: 365 days)
        """
        self.cache.set(f"blacklist:{token}", "1", ttl=ttl)

    def validate_access_token(self, token: str) -> str | None:
        """
        Validate access token and return user ID.

        Args:
            token: Access token to validate

        Returns:
            User ID if valid, None otherwise
        """
        from app.core.security import decode_access_token

        payload = decode_access_token(token)
        if payload is None:
            return None

        return payload.get("sub")
