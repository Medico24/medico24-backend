"""Firebase Admin SDK initialization and utilities."""

import os

import firebase_admin
from firebase_admin import auth, credentials
from structlog import get_logger

logger = get_logger(__name__)

_firebase_app: firebase_admin.App | None = None


def initialize_firebase(credentials_path: str | None = None) -> None:
    """
    Initialize Firebase Admin SDK.

    Args:
        credentials_path: Optional path to service account JSON file.
                         If not provided, will check environment variables.

    Looks for Firebase credentials in order:
    1. credentials_path parameter
    2. FIREBASE_CREDENTIALS_PATH environment variable
    3. GOOGLE_APPLICATION_CREDENTIALS environment variable
    4. Default application credentials

    Note: For production, use FIREBASE_CREDENTIALS_PATH or service account JSON.
    For development, you can use Application Default Credentials.
    """
    global _firebase_app

    if _firebase_app is not None:
        logger.info("Firebase already initialized")
        return

    try:
        # Check for explicit Firebase credentials path
        cred_path = (
            credentials_path
            or os.getenv("FIREBASE_CREDENTIALS_PATH")
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )

        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with service account", path=cred_path)
        else:
            # Try to initialize with default credentials
            _firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase initialized with default credentials")

    except Exception as e:
        logger.error("Failed to initialize Firebase", error=str(e))
        raise


def get_firebase_app() -> firebase_admin.App:
    """
    Get the Firebase app instance.

    Returns:
        Firebase app instance

    Raises:
        RuntimeError: If Firebase is not initialized
    """
    if _firebase_app is None:
        raise RuntimeError("Firebase not initialized. Call initialize_firebase() first.")
    return _firebase_app


async def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token.

    Args:
        id_token: Firebase ID token from the client

    Returns:
        Decoded token containing user information

    Raises:
        ValueError: If token is invalid or expired
        firebase_admin.auth.InvalidIdTokenError: If token verification fails
    """
    try:
        # Verify the token and get user claims
        # check_revoked=False for better performance, clock_skew_seconds=10 to tolerate clock differences
        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10)

        logger.info(
            "Firebase token verified",
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email"),
        )

        return decoded_token

    except auth.InvalidIdTokenError as e:
        logger.warning("Invalid Firebase ID token", error=str(e))
        raise ValueError(f"Invalid Firebase ID token: {e!s}")
    except auth.ExpiredIdTokenError as e:
        logger.warning("Expired Firebase ID token", error=str(e))
        raise ValueError("Firebase ID token has expired")
    except Exception as e:
        logger.error("Firebase token verification failed", error=str(e))
        raise ValueError(f"Token verification failed: {e!s}")
