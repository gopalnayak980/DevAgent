"""
Approval API routes — Phase 6: Human-in-the-Loop.

Provides REST endpoints for creating, listing, retrieving,
approving, rejecting, and cancelling approval requests.

Security: Approval/rejection can ONLY happen via explicit API calls
from the user. The AI can create approval requests but cannot
approve them itself.
"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import User
from app.auth.dependencies import get_current_active_user
from app.hitl.repository import ApprovalRepository
from app.hitl.service import (
    HumanApprovalService,
    ApprovalNotFoundError,
    InvalidTransitionError,
)
from app.hitl.schemas import (
    ApprovalCreateRequest,
    ApprovalResponse,
    ApprovalListResponse,
    ApprovalActionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["approvals"])


def _get_service(session: AsyncSession) -> HumanApprovalService:
    """Build the service with its repository from the injected session."""
    return HumanApprovalService(ApprovalRepository(session))


# ---------------------------------------------------------------------------
# POST /api/approvals — Create an approval request
# ---------------------------------------------------------------------------

@router.post("/approvals", response_model=ApprovalResponse, status_code=201)
async def create_approval(
    request: ApprovalCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new approval request."""
    service = _get_service(session)
    user_id = current_user.id

    approval = await service.create_approval(
        user_id=user_id,
        action_type=request.action_type,
        description=request.description,
    )
    return ApprovalResponse.model_validate(approval)


# ---------------------------------------------------------------------------
# GET /api/approvals — List approval requests
# ---------------------------------------------------------------------------

@router.get("/approvals", response_model=ApprovalListResponse)
async def list_approvals(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all approval requests for current user."""
    service = _get_service(session)
    approvals = await service.list_approvals(user_id=current_user.id)
    return ApprovalListResponse(
        approvals=[ApprovalResponse.model_validate(a) for a in approvals],
        total=len(approvals),
    )


# ---------------------------------------------------------------------------
# GET /api/approvals/{approval_id} — Get a single approval request
# ---------------------------------------------------------------------------

@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single approval request by ID."""
    service = _get_service(session)
    try:
        approval = await service.get_approval(approval_id)
        if approval.user_id != current_user.id:
            raise ApprovalNotFoundError()
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")
    return ApprovalResponse.model_validate(approval)


# ---------------------------------------------------------------------------
# POST /api/approvals/{approval_id}/approve — Approve a request
# ---------------------------------------------------------------------------

@router.post("/approvals/{approval_id}/approve", response_model=ApprovalActionResponse)
async def approve_request(
    approval_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Approve a pending approval request."""
    service = _get_service(session)
    try:
        approval = await service.get_approval(approval_id)
        if approval.user_id != current_user.id:
            raise ApprovalNotFoundError()
        approval = await service.approve(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Execute the protected action after approval
    execution = await service.execute_if_approved(approval_id)

    return ApprovalActionResponse(
        id=approval.id,
        status=approval.status,
        message=execution.get("result", "Approved."),
    )


# ---------------------------------------------------------------------------
# POST /api/approvals/{approval_id}/reject — Reject a request
# ---------------------------------------------------------------------------

@router.post("/approvals/{approval_id}/reject", response_model=ApprovalActionResponse)
async def reject_request(
    approval_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reject a pending approval request."""
    service = _get_service(session)
    try:
        approval = await service.get_approval(approval_id)
        if approval.user_id != current_user.id:
            raise ApprovalNotFoundError()
        approval = await service.reject(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ApprovalActionResponse(
        id=approval.id,
        status=approval.status,
        message="Approval request has been rejected. The protected action was not executed.",
    )


# ---------------------------------------------------------------------------
# POST /api/approvals/{approval_id}/cancel — Cancel a request
# ---------------------------------------------------------------------------

@router.post("/approvals/{approval_id}/cancel", response_model=ApprovalActionResponse)
async def cancel_request(
    approval_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel a pending approval request."""
    service = _get_service(session)
    try:
        approval = await service.get_approval(approval_id)
        if approval.user_id != current_user.id:
            raise ApprovalNotFoundError()
        approval = await service.cancel(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ApprovalActionResponse(
        id=approval.id,
        status=approval.status,
        message="Approval request has been cancelled.",
    )


# ---------------------------------------------------------------------------
# POST /api/approvals/{approval_id}/execute — Execute an approved action
# ---------------------------------------------------------------------------

@router.post("/approvals/{approval_id}/execute")
async def execute_approved_action(
    approval_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Execute the protected action for an approved request.

    Returns the execution result. Only approved requests will execute.
    """
    service = _get_service(session)
    try:
        approval = await service.get_approval(approval_id)
        if approval.user_id != current_user.id:
            raise ApprovalNotFoundError()
        result = await service.execute_if_approved(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")

    if not result["executed"]:
        raise HTTPException(status_code=400, detail=result["result"])

    return result
