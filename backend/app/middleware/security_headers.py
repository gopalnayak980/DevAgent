"""
Phase 10.1 — Security Headers Middleware.

Adds security-related HTTP response headers to every response.
These headers protect against common web vulnerabilities such as
clickjacking, MIME-type sniffing, and information leakage.

CSP is intentionally permissive for local development (Vite HMR
uses inline scripts and eval). Production deployments should
tighten CSP via the CONTENT_SECURITY_POLICY environment variable.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        # CSP: configurable via env var, defaults to a permissive dev policy
        response.headers["Content-Security-Policy"] = settings.CONTENT_SECURITY_POLICY

        return response
