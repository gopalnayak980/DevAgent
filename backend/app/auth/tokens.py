"""
Phase 10.2 — JWT Token Service.

Creates and verifies JWT access tokens.
- JWT_SECRET_KEY MUST be set in the environment.
- Never hardcode the secret.
- Tokens use HS256 by default (configurable via JWT_ALGORITHM).
- Expired/invalid tokens raise HTTP 401 (never 500).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)

# Claims used inside the JWT payload
_ALGORITHM = settings.JWT_ALGORITHM
_SECRET_KEY = settings.JWT_SECRET_KEY


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: The authenticated user's database ID.
        email: The user's email address (informational — NOT for auth decisions).
        role: The user's role ('user' or 'admin').
        expires_delta: Custom expiry duration; falls back to settings value.

    Returns:
        A signed JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": user_id,          # Subject: user ID (authoritative)
        "email": email,           # Informational only
        "role": role,             # Role for authorization checks
        "iat": now,               # Issued at
        "exp": expire,            # Expiry
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dict.

    Raises:
        HTTPException 401: If the token is missing, expired, or malformed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception
