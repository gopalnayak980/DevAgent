"""
Phase 10.2 — Authentication Service.

Business logic for user registration and login.
- Normalizes email to lowercase before storage.
- Hashes password before storage — plaintext is never persisted.
- Duplicate email detection returns 409 Conflict.
- Login failures return a generic 401 to avoid email enumeration.
"""

import logging

from fastapi import HTTPException, status

from app.database.models import User
from app.auth.repository import UserRepository
from app.auth.password import hash_password, verify_password
from app.auth.tokens import create_access_token
from app.auth.schemas import RegisterRequest, LoginRequest, UserResponse, TokenResponse, RegisterResponse

logger = logging.getLogger(__name__)


class AuthService:
    """Service for user registration, login, and token issuance."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def register(self, request: RegisterRequest) -> RegisterResponse:
        """Register a new user.

        Steps:
        1. Check for duplicate email.
        2. Hash the password.
        3. Create User with role='user' (hardcoded — cannot be elevated via API).
        4. Issue a JWT access token.
        5. Return token + safe user profile.

        Raises:
            HTTPException 409: If the email is already registered.
        """
        # Email is already normalized by the schema validator
        existing = await self.repository.get_by_email(request.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        # Hash password — plaintext is never stored
        password_hash = hash_password(request.password)

        user = User(
            name=request.name,
            email=request.email,       # Already normalized
            password_hash=password_hash,
            role="user",               # ALWAYS 'user' — cannot be set via API
            is_active=True,
        )
        created_user = await self.repository.create(user)
        logger.info("Registered new user id=%s email=%s", created_user.id, created_user.email)

        token = create_access_token(
            user_id=created_user.id,
            email=created_user.email,
            role=created_user.role,
        )

        return RegisterResponse(
            access_token=token,
            user=UserResponse.model_validate(created_user),
        )

    async def login(self, request: LoginRequest) -> TokenResponse:
        """Authenticate an existing user and issue a JWT.

        The error message is intentionally generic to prevent email enumeration:
        both 'wrong password' and 'email not found' return the same 401.

        Raises:
            HTTPException 401: If credentials are invalid.
            HTTPException 403: If the account is deactivated.
        """
        _auth_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        user = await self.repository.get_by_email(request.email)
        if user is None:
            raise _auth_error

        if not verify_password(request.password, user.password_hash):
            raise _auth_error

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated.",
            )

        token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )
        logger.info("User logged in id=%s", user.id)

        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
