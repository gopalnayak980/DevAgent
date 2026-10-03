"""
HITL Service — Phase 6.

Business logic for human-in-the-loop approval workflows.

Key security principle: the AI can REQUEST approval, but only an
explicit API action by a human can GRANT approval. The service
enforces state-machine transitions and prevents self-approval.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.database.models import ApprovalRequest
from app.hitl.repository import ApprovalRepository

logger = logging.getLogger(__name__)

# Valid status transitions: from_status -> set of allowed to_statuses
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected", "cancelled"},
}


class InvalidTransitionError(Exception):
    """Raised when an invalid approval state transition is attempted."""
    pass


class ApprovalNotFoundError(Exception):
    """Raised when an approval request is not found."""
    pass


class HumanApprovalService:
    """Service for managing human-in-the-loop approval requests.

    Architecture:
        Route → HumanApprovalService → ApprovalRepository → Database
    """

    def __init__(self, repository: ApprovalRepository) -> None:
        self.repository = repository

    async def create_approval(
        self,
        user_id: str,
        action_type: str,
        description: str,
    ) -> ApprovalRequest:
        """Create a new approval request with status 'pending'.

        Args:
            user_id: The user who triggered the action.
            action_type: Identifier for the type of action.
            description: Human-readable description.

        Returns:
            The created ApprovalRequest.
        """
        approval = ApprovalRequest(
            user_id=user_id,
            action_type=action_type,
            description=description,
            status="pending",
        )
        created = await self.repository.create(approval)
        logger.info(
            "Created approval request id=%s action_type=%s status=pending",
            created.id,
            action_type,
        )
        return created

    async def get_approval(self, approval_id: str) -> ApprovalRequest:
        """Retrieve a single approval request.

        Raises:
            ApprovalNotFoundError: If no request with the given ID exists.
        """
        approval = await self.repository.get_by_id(approval_id)
        if approval is None:
            raise ApprovalNotFoundError(f"Approval request '{approval_id}' not found.")
        return approval

    async def list_approvals(self, user_id: Optional[str] = None) -> list[ApprovalRequest]:
        """List all approval requests, optionally filtered by user."""
        return await self.repository.list_all(user_id=user_id)

    async def approve(self, approval_id: str) -> ApprovalRequest:
        """Approve a pending request.

        Raises:
            ApprovalNotFoundError: If no request with the given ID exists.
            InvalidTransitionError: If the request is not in 'pending' status.
        """
        return await self._transition(approval_id, "approved")

    async def reject(self, approval_id: str) -> ApprovalRequest:
        """Reject a pending request.

        Raises:
            ApprovalNotFoundError: If no request with the given ID exists.
            InvalidTransitionError: If the request is not in 'pending' status.
        """
        return await self._transition(approval_id, "rejected")

    async def cancel(self, approval_id: str) -> ApprovalRequest:
        """Cancel a pending request.

        Raises:
            ApprovalNotFoundError: If no request with the given ID exists.
            InvalidTransitionError: If the request is not in 'pending' status.
        """
        return await self._transition(approval_id, "cancelled")

    async def check_status(self, approval_id: str) -> str:
        """Return the current status of an approval request.

        Raises:
            ApprovalNotFoundError: If no request with the given ID exists.
        """
        approval = await self.get_approval(approval_id)
        return approval.status

    async def execute_if_approved(self, approval_id: str) -> dict:
        """Execute the protected demo action only if the request is approved.

        This method demonstrates that a protected action will NOT execute
        unless the approval status is 'approved'.

        Returns:
            A dict with 'executed' bool and a 'result' message.

        Raises:
            ApprovalNotFoundError: If no request with the given ID exists.
        """
        approval = await self.get_approval(approval_id)

        if approval.status != "approved":
            logger.info(
                "Protected action NOT executed for approval id=%s — status=%s",
                approval_id,
                approval.status,
            )
            return {
                "executed": False,
                "result": (
                    f"Action not executed. Current status is '{approval.status}'. "
                    f"Only approved requests can be executed."
                ),
            }

        # Execute the safe demo action
        result = _demo_protected_action()
        logger.info("Protected action EXECUTED for approval id=%s", approval_id)
        return {
            "executed": True,
            "result": result,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _transition(self, approval_id: str, target_status: str) -> ApprovalRequest:
        """Attempt a state transition on an approval request.

        Enforces the state machine:
            pending → approved | rejected | cancelled

        All other transitions are invalid.
        """
        approval = await self.get_approval(approval_id)
        allowed = _VALID_TRANSITIONS.get(approval.status, set())

        if target_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition from '{approval.status}' to '{target_status}'. "
                f"Only pending requests can be {target_status}."
            )

        approval.status = target_status
        approval.resolved_at = datetime.utcnow()
        updated = await self.repository.update(approval)

        logger.info(
            "Approval id=%s transitioned to '%s'",
            approval_id,
            target_status,
        )
        return updated


def _demo_protected_action() -> str:
    """A safe, simulated protected action for Phase 6 demonstration.

    This is intentionally trivial — no file I/O, no network calls,
    no destructive operations. It simply returns a success message.
    """
    return (
        "✅ Demo protected action executed successfully! "
        "This simulates an action that required human approval before running."
    )
