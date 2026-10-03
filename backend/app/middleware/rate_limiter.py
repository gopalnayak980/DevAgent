"""
Phase 10.1 — Simple In-Memory Rate Limiter Middleware.

Provides basic per-IP rate limiting using a sliding-window counter
stored in an in-memory dictionary.

IMPORTANT LIMITATIONS:
- This is a DEVELOPMENT-ONLY in-memory rate limiter.
- It does NOT persist across application restarts.
- It does NOT work in multi-process deployments.
- Production deployments MUST use a distributed rate limiter
  backed by Redis or a similar shared store.

Configurable via environment variables:
- RATE_LIMIT_REQUESTS: max requests per window (default: 30)
- RATE_LIMIT_WINDOW_SECONDS: sliding window in seconds (default: 60)
"""

import time
import logging
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)

# Rate-limited paths (only expensive / public-facing endpoints)
_RATE_LIMITED_PATHS = {"/api/chat", "/api/jobs"}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter.

    Only applies to specific expensive API endpoints.
    Not suitable for production multi-process deployments.
    """

    def __init__(self, app):
        super().__init__(app)
        # {ip_address: [timestamp, timestamp, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _clean_old_requests(self, ip: str, now: float) -> None:
        """Remove timestamps outside the current window."""
        window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS
        self._requests[ip] = [
            ts for ts in self._requests[ip] if ts > window_start
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit specific paths
        if request.url.path not in _RATE_LIMITED_PATHS:
            return await call_next(request)

        # Only rate-limit POST requests (GET listing is cheap)
        if request.method != "POST":
            return await call_next(request)

        ip = request.headers.get("x-forwarded-for")
        if not ip:
            ip = request.client.host if request.client else "unknown"
            
        now = time.time()

        self._clean_old_requests(ip, now)

        if len(self._requests[ip]) >= settings.RATE_LIMIT_REQUESTS:
            logger.warning(
                "Rate limit exceeded for IP %s on %s",
                ip, request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please wait before trying again."
                },
            )

        self._requests[ip].append(now)
        return await call_next(request)
