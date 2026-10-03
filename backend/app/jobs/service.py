"""
Job Service — Phase 7.

Business logic for background job management.

Enforces the job lifecycle state machine:
    pending → running → completed
    pending → cancelled
    pending/running → failed

Invalid state transitions are rejected.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.database.models import Job
from app.jobs.repository import JobRepository

logger = logging.getLogger(__name__)

# Valid job types
VALID_JOB_TYPES = {"agent_task"}

# Valid status transitions: from_status → set of allowed to_statuses
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "cancelled", "failed"},
    "running": {"completed", "failed"},
}


class JobNotFoundError(Exception):
    """Raised when a job is not found."""
    pass


class InvalidJobTransitionError(Exception):
    """Raised when an invalid job state transition is attempted."""
    pass


class InvalidJobTypeError(Exception):
    """Raised when an unsupported job type is requested."""
    pass


class JobService:
    """Service for managing background jobs.

    Architecture:
        Route → JobService → JobRepository → Database
    """

    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def create_job(
        self,
        user_id: str,
        message: str,
        job_type: str = "agent_task",
    ) -> Job:
        """Create a new background job with status 'pending'.

        Args:
            user_id: The user who submitted the job.
            message: The task input.
            job_type: Type of job (currently only 'agent_task').

        Returns:
            The created Job.

        Raises:
            InvalidJobTypeError: If the job type is not supported.
        """
        if job_type not in VALID_JOB_TYPES:
            raise InvalidJobTypeError(
                f"Unsupported job type '{job_type}'. "
                f"Supported types: {', '.join(VALID_JOB_TYPES)}"
            )

        job = Job(
            user_id=user_id,
            job_type=job_type,
            input=message,
            status="pending",
        )
        created = await self.repository.create(job)
        logger.info(
            "Created job id=%s type=%s status=pending",
            created.id,
            job_type,
        )
        return created

    async def get_job(self, job_id: str) -> Job:
        """Retrieve a single job.

        Raises:
            JobNotFoundError: If no job with the given ID exists.
        """
        job = await self.repository.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(f"Job '{job_id}' not found.")
        return job

    async def list_jobs(self, user_id: Optional[str] = None) -> list[Job]:
        """List all jobs, optionally filtered by user."""
        return await self.repository.list_all(user_id=user_id)

    async def cancel_job(self, job_id: str) -> Job:
        """Cancel a pending job.

        Only pending jobs can be cancelled. Running jobs cannot be
        safely interrupted via this method.

        Raises:
            JobNotFoundError: If no job with the given ID exists.
            InvalidJobTransitionError: If the job is not in 'pending' status.
        """
        job = await self.get_job(job_id)
        allowed = _VALID_TRANSITIONS.get(job.status, set())

        if "cancelled" not in allowed:
            raise InvalidJobTransitionError(
                f"Cannot cancel job in '{job.status}' status. "
                f"Only pending jobs can be cancelled."
            )

        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        updated = await self.repository.update(job)

        logger.info("Job id=%s cancelled", job_id)
        return updated
