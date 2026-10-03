"""
Phase 10.1 — Request Size Limiting Middleware.

Rejects requests with bodies larger than the configured maximum size.
Prevents DOS attacks via excessively large payloads.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Reject requests with excessively large bodies."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large."},
                )

        return await call_next(request)
