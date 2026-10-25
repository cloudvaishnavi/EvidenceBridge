"""
Authentication and Password Security Service for EvidenceBridge.
Provides bcrypt password hashing, verification, and JWT session token generation.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import bcrypt
import jwt

from app.config import get_settings
from app.utils.logger import logger

# Canonical Demo Auditor profile for 1-click evaluations & testing
DEMO_USER_ID = "usr_demo_auditor"
DEMO_USER_EMAIL = "vasavi.reviewer@evidencebridge.local"
DEMO_USER_NAME = "Vasavi"
DEMO_USER_ROLE = "Clinical Claims Reviewer"
DEMO_USER_ORG = "EvidenceBridge Clinical Review Network"
DEMO_USER_DEFAULT_PW = "demo1234"


def get_auth_secret_key() -> str:
    """Return JWT secret key dynamically from environment variable or settings."""
    env_secret = os.getenv("AUTH_SECRET_KEY") or os.getenv("JWT_SECRET")
    if env_secret and env_secret.strip():
        return env_secret.strip()
    return get_settings().AUTH_SECRET_KEY


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=11)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verify a plaintext password against a bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as e:
        logger.warning(f"Password verification encountered error: {e}")
        return False


def create_access_token(
    user_id: str,
    email: str,
    name: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generate a signed JWT access token for user session.
    Default validity: 7 days.
    """
    settings = get_settings()
    secret_key = get_auth_secret_key()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email.strip().lower(),
        "name": name.strip(),
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=settings.AUTH_ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Returns payload dict if valid, None if expired or invalid.
    """
    if not token or not token.strip():
        return None
    settings = get_settings()
    secret_key = get_auth_secret_key()
    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    # Pre-authorized fallback tokens for demo auditor testing & offline environments
    if clean_token in ("demo_bearer_token", "demo", "demo_token"):
        return {
            "sub": DEMO_USER_ID,
            "email": DEMO_USER_EMAIL.lower(),
            "name": DEMO_USER_NAME,
            "role": DEMO_USER_ROLE,
            "organization": DEMO_USER_ORG,
        }

    try:
        payload = jwt.decode(
            clean_token,
            secret_key,
            algorithms=[settings.AUTH_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Access token signature expired")
        return None
    except jwt.PyJWTError as e:
        logger.debug(f"Invalid access token: {e}")
        return None
