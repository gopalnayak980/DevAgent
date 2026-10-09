"""
FastAPI application entry point — Phase 10.1: Security Foundation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings, validate_settings
from app.database.session import engine
from app.database.models import Base
from app.routes.chat import router as chat_router
from app.routes.approvals import router as approvals_router
from app.routes.jobs import router as jobs_router
from app.routes.observability import router as observability_router
from app.routes.auth import router as auth_router
from app.tools.calculator import CalculatorTool
from app.tools.registry import get_registry
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.request_size import RequestSizeMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    # We will let Alembic handle schema migrations going forward.
    # We still call create_all for development ease if DB is completely empty, 
    # but Alembic will manage ongoing migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="DevAgent API",
    description="AI Software Engineering Assistant — Phase 10.2: Authentication",
    version="0.10.2",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 10.1: Security Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestSizeMiddleware)

# Register routes
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(approvals_router)
app.include_router(jobs_router)
app.include_router(observability_router)

# ---------------------------------------------------------------------------
# Phase 4 — Register tools at startup
# ---------------------------------------------------------------------------
registry = get_registry()
registry.register(CalculatorTool())


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "application": "DevAgent",
        "version": "0.10.1",
        "phase": 10.1,
    }

@app.get("/api/health")
async def health_check():
    """Phase 10.3: Backend health check endpoint."""
    return {
        "status": "ok",
        "service": "DevAgent backend"
    }
