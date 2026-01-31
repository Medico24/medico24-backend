"""Firebase Admin SDK initialization and utilities."""

import json
import os

import firebase_admin
from firebase_admin import auth, credentials
from structlog import get_logger

logger = get_logger(__name__)

_firebase_app: firebase_admin.App | None = None


def initialize_firebase(
    firebase_credentials_path: str | None = None, firebase_config_json: str | None = None
) -> None:
    """
    Initialize Firebase Admin SDK.

    Args:
        firebase_config_json: Optional raw JSON string of service account.
        firebase_credentials_path: Optional path to service account JSON file.

    Looks for Firebase credentials in order:
    1. credentials_path parameter
    2. FIREBASE_CONFIG_JSON environment variable
    3. FIREBASE_CREDENTIALS_PATH environment variable
    4. Default application credentials

    Note: For production, use FIREBASE_CREDENTIALS_PATH or service account JSON.
    For development, you can use Application Default Credentials.
    """
    global _firebase_app

    if _firebase_app is not None:
        logger.info("Firebase already initialized")
        return

    try:
        cred = None

        # 1. Try raw JSON string (Vercel / Production)
        if firebase_config_json:
            logger.info("Initializing Firebase with JSON string from environment")
            cred_dict = json.loads(firebase_config_json)
            cred = credentials.Certificate(cred_dict)

        # 2. Fallback to File Path (Local Dev)
        elif firebase_credentials_path and os.path.exists(firebase_credentials_path):
            logger.info("Initializing Firebase with JSON file", path=firebase_credentials_path)
            cred = credentials.Certificate(firebase_credentials_path)

        if cred:
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Last resort: Try default credentials
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
        logger.warning("Invalid or expired Firebase ID token", error=str(e))
        raise ValueError(f"Invalid Firebase ID token: {e!s}")
    except Exception as e:
        logger.error("Firebase token verification failed", error=str(e))
        raise ValueError(f"Token verification failed: {e!s}")
