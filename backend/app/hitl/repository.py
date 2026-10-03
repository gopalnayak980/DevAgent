"""
HITL Repository — Phase 6.

Data access layer for approval requests. All database interactions
go through this repository. The service layer handles business logic.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApprovalRequest


class ApprovalRepository:
    """Repository for ApprovalRequest CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        """Persist a new approval request."""
        self.session.add(approval)
        await self.session.commit()
        await self.session.refresh(approval)
        return approval

    async def get_by_id(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Retrieve a single approval request by ID."""
        result = await self.session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, user_id: Optional[str] = None) -> List[ApprovalRequest]:
        """List approval requests, optionally filtered by user_id."""
        stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
        if user_id:
            stmt = stmt.where(ApprovalRequest.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, approval: ApprovalRequest) -> ApprovalRequest:
        """Update an existing approval request."""
        await self.session.commit()
        await self.session.refresh(approval)
        return approval
