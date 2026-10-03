"""
Observability API routes — Phase 8: Evaluation & Observability.

Provides REST endpoints for viewing execution traces and aggregate
statistics. Read-only endpoints for inspecting what happened during
AI task execution.
"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import User
from app.auth.dependencies import get_current_active_user, require_admin
from app.observability.repository import TraceRepository
from app.observability.service import TraceService
from app.observability.schemas import (
    TraceResponse,
    TraceListResponse,
    ObservabilityStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/observability", tags=["observability"])


def _get_service(session: AsyncSession) -> TraceService:
    """Build the service with its repository from the injected session."""
    return TraceService(TraceRepository(session))


# ---------------------------------------------------------------------------
# GET /api/observability/traces — List recent traces
# ---------------------------------------------------------------------------

@router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List recent execution traces."""
    service = _get_service(session)
    user_id = None if current_user.role == "admin" else current_user.id
    traces = await service.list_traces(user_id=user_id)
    return TraceListResponse(
        traces=[TraceService.trace_to_response(t) for t in traces],
        total=len(traces),
    )


# ---------------------------------------------------------------------------
# GET /api/observability/traces/{trace_id} — Get a single trace
# ---------------------------------------------------------------------------

@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single execution trace by ID."""
    service = _get_service(session)
    trace = await service.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found.")
    
    if current_user.role != "admin" and trace.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this trace.")
        
    return TraceService.trace_to_response(trace)


# ---------------------------------------------------------------------------
# GET /api/observability/stats — Aggregate statistics
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=ObservabilityStats)
async def get_stats(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get aggregate observability statistics."""
    service = _get_service(session)
    user_id = None if current_user.role == "admin" else current_user.id
    return await service.get_stats(user_id=user_id)
