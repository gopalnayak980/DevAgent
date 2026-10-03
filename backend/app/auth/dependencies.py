"""
Phase 10.2 — FastAPI Authentication Dependencies.

Provides reusable dependencies for:
- Extracting and validating the Bearer token from incoming requests.
- Loading the current user from the database.
- Enforcing 'active user' and 'admin role' constraints.

Usage in routes:
    current_user: User = Depends(get_current_active_user)
    _: User = Depends(require_admin)
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import User
from app.auth.tokens import decode_access_token
from app.auth.repository import UserRepository

logger = logging.getLogger(__name__)

# Bearer token extractor — auto_error=False so we can return a clean 401
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Extract, decode, and return the currently authenticated User.

    The user's identity comes exclusively from the verified JWT —
    never from a user-supplied body parameter.

    Raises:
        HTTPException 401: Missing token, malformed token, expired token,
                           or user not found in the database.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id: str = payload.get("sub")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the current user is active.

    Raises:
        HTTPException 403: If the account is deactivated.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Restrict access to admin users only.

    Raises:
        HTTPException 403: If the user does not have the 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required.",
        )
    return current_user
