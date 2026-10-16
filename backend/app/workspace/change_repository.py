"""
File Change Proposal Repository — Phase 11.4.

Data access layer for FileChangeProposal model.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import FileChangeProposal


class FileChangeProposalRepository:
    """Repository for FileChangeProposal CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, proposal: FileChangeProposal) -> FileChangeProposal:
        """Persist a new file change proposal."""
        self.session.add(proposal)
        await self.session.commit()
        await self.session.refresh(proposal)
        return proposal

    async def get_by_id(self, proposal_id: str) -> Optional[FileChangeProposal]:
        """Retrieve a proposal by ID."""
        result = await self.session.execute(
            select(FileChangeProposal).where(FileChangeProposal.id == proposal_id)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: str,
        status: Optional[str] = None,
    ) -> List[FileChangeProposal]:
        """List proposals for a workspace, optionally filtered by status."""
        query = (
            select(FileChangeProposal)
            .where(FileChangeProposal.workspace_id == workspace_id)
            .order_by(FileChangeProposal.created_at.desc())
        )
        if status:
            query = query.where(FileChangeProposal.status == status)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, proposal: FileChangeProposal) -> FileChangeProposal:
        """Persist updates to an existing proposal."""
        await self.session.commit()
        await self.session.refresh(proposal)
        return proposal
