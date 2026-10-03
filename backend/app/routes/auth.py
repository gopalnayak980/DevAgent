"""
Phase 10.2 — Authentication API Routes.

POST /api/auth/register  — Create a new user account.
POST /api/auth/login     — Authenticate and receive a JWT.
GET  /api/auth/me        — Return the current user's profile.
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import User
from app.auth.repository import UserRepository
from app.auth.service import AuthService
from app.auth.schemas import RegisterRequest, LoginRequest, UserResponse, TokenResponse, RegisterResponse
from app.auth.dependencies import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_service(session: AsyncSession) -> AuthService:
    """Build the AuthService with a fresh repository for the request session."""
    return AuthService(UserRepository(session))


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """Register a new user account.

    - Email is normalized to lowercase.
    - Password is hashed before storage.
    - Role is always set to 'user' — cannot be elevated via this endpoint.
    - Returns an access token on success.
    - Returns 409 if the email is already registered.
    """
    service = _get_service(session)
    return await service.register(request)


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password.

    Returns a JWT access token on success.
    Returns 401 for any credential failure (intentionally generic to prevent
    email enumeration).
    """
    service = _get_service(session)
    return await service.login(request)


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """Return the current authenticated user's profile.

    Requires a valid Bearer token in the Authorization header.
    Returns 401 if unauthenticated; 403 if account is inactive.
    """
    return UserResponse.model_validate(current_user)
