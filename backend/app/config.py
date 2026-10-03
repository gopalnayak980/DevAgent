"""
Application configuration loaded from environment variables.

Phase 10.1: Adds security-related settings and startup validation.
"""

import os
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Application settings sourced from environment variables."""

    # LLM Configuration
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))

    # CORS — environment-driven, never allow_origins=["*"] with credentials
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

    # Validation
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "4000"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./devagent.db")

    # Celery / Redis (Phase 7)
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # -----------------------------------------------------------------------
    # Phase 10.1 — Security settings
    # -----------------------------------------------------------------------

    # Rate limiting (in-memory, development only)
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Maximum request body size in bytes (1 MB default)
    MAX_REQUEST_BODY_BYTES: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(1024 * 1024)))

    # Content-Security-Policy header value.
    # Default is permissive for local Vite dev (inline scripts, eval for HMR).
    # Production deployments should set a strict CSP via environment variable.
    CONTENT_SECURITY_POLICY: str = os.getenv(
        "CONTENT_SECURITY_POLICY",
        "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "font-src 'self' data:; connect-src 'self' http://localhost:* ws://localhost:*",
    )


    # -----------------------------------------------------------------------
    # Phase 10.2 — Authentication settings
    # -----------------------------------------------------------------------
    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


# Singleton settings instance
settings = Settings()


# ---------------------------------------------------------------------------
# Phase 10.1 & 10.2 — Startup validation
# ---------------------------------------------------------------------------

_SECRET_FIELDS = {"LLM_API_KEY", "JWT_SECRET_KEY"}
_REDACTED_FIELDS = {
    "LLM_API_KEY", "DATABASE_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", "JWT_SECRET_KEY"
}


def validate_settings() -> list[str]:
    """Validate critical settings at startup.

    Returns a list of warning messages. Does NOT raise — development
    environments may have missing keys intentionally.
    """
    warnings: list[str] = []

    if not settings.LLM_API_KEY:
        warnings.append(
            "LLM_API_KEY is not set. LLM features will not work."
        )

    if not settings.LLM_MODEL:
        warnings.append(
            "LLM_MODEL is not set. LLM features will not work."
        )

    if "*" in settings.CORS_ORIGINS:
        warnings.append(
            "CORS_ORIGINS contains '*'. This is insecure when credentials are enabled. "
            "Use explicit origins in production."
        )

    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "CHANGE_ME_IN_PRODUCTION_OR_ELSE":
        warnings.append(
            "JWT_SECRET_KEY is missing or set to a default value. Authentication is insecure!"
        )

    for w in warnings:
        logger.warning("CONFIG WARNING: %s", w)

    return warnings


def safe_settings_summary() -> dict:
    """Return a sanitized summary of settings for diagnostics.

    Never exposes secrets. Used only for internal logging, never
    returned to API consumers.
    """
    return {
        "LLM_MODEL": settings.LLM_MODEL or "(not set)",
        "LLM_BASE_URL": settings.LLM_BASE_URL or "(not set)",
        "LLM_TIMEOUT_SECONDS": settings.LLM_TIMEOUT_SECONDS,
        "CORS_ORIGINS": settings.CORS_ORIGINS,
        "MAX_MESSAGE_LENGTH": settings.MAX_MESSAGE_LENGTH,
        "RATE_LIMIT_REQUESTS": settings.RATE_LIMIT_REQUESTS,
        "RATE_LIMIT_WINDOW_SECONDS": settings.RATE_LIMIT_WINDOW_SECONDS,
        "DATABASE_URL": "(configured)" if settings.DATABASE_URL else "(not set)",
    }

