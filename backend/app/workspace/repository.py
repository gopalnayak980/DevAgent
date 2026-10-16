"""
Workspace Repository — Phase 11.

Data access layer for the Workspace model. All database interactions
go through this repository. The service layer handles business logic.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workspace


class WorkspaceRepository:
    """Repository for Workspace CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, workspace: Workspace) -> Workspace:
        """Persist a new workspace."""
        self.session.add(workspace)
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Retrieve a single workspace by ID."""
        result = await self.session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> List[Workspace]:
        """List all workspaces owned by a given user, ordered by creation date."""
        result = await self.session.execute(
            select(Workspace)
            .where(Workspace.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_name(self, user_id: str, name: str) -> Optional[Workspace]:
        """Retrieve a workspace by owner and name (for uniqueness checks)."""
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.user_id == user_id,
                Workspace.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, workspace: Workspace) -> Workspace:
        """Persist updates to an existing workspace."""
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace
