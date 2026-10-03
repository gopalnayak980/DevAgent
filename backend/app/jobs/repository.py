"""
Job Repository — Phase 7.

Data access layer for background jobs. All database interactions
go through this repository. The service layer handles business logic.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Job


class JobRepository:
    """Repository for Job CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job: Job) -> Job:
        """Persist a new job."""
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        """Retrieve a single job by ID."""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, user_id: Optional[str] = None) -> List[Job]:
        """List jobs, optionally filtered by user_id."""
        stmt = select(Job).order_by(Job.created_at.desc())
        if user_id:
            stmt = stmt.where(Job.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, job: Job) -> Job:
        """Update an existing job."""
        await self.session.commit()
        await self.session.refresh(job)
        return job
