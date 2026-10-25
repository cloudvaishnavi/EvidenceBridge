"""
Authentication and Password Security Service for EvidenceBridge.
Provides bcrypt password hashing, verification, and JWT session token generation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import bcrypt
import jwt

from app.config import get_settings
from app.utils.logger import logger

# Canonical Demo Auditor profile for 1-click evaluations & testing
DEMO_USER_ID = "usr_demo_auditor"
DEMO_USER_EMAIL = "sarah.chen@stjudehealth.org"
DEMO_USER_NAME = "Dr. Sarah Chen, MD"
DEMO_USER_ROLE = "Senior Clinical Claims Reviewer"
DEMO_USER_ORG = "St. Jude Metropolitan Health System"
DEMO_USER_DEFAULT_PW = "demo1234"


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
        settings.AUTH_SECRET_KEY,
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
    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    try:
        payload = jwt.decode(
            clean_token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Access token signature expired")
        return None
    except jwt.PyJWTError as e:
        logger.debug(f"Invalid access token: {e}")
        return None
