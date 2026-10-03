"""
Phase 10.2 — Authentication Pydantic Schemas.

Defines request/response models for registration, login, and user profile.
Password hash is NEVER included in any response schema.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Registration request payload."""

    name: str = Field(..., min_length=1, max_length=100, description="Display name.")
    email: EmailStr = Field(..., description="Email address (normalized to lowercase).")
    password: str = Field(..., min_length=8, description="Password (min 8 characters).")
    confirm_password: str = Field(..., description="Must match password.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v


class LoginRequest(BaseModel):
    """Login request payload."""

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(..., description="Account password.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


# ---------------------------------------------------------------------------
# Response schemas — password_hash is intentionally excluded
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """Safe user profile — never includes password_hash."""

    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterResponse(BaseModel):
    """Successful registration response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
