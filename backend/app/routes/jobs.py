"""
Jobs API routes — Phase 7: Background Agent Workflows.

Provides REST endpoints for creating, listing, checking status,
and cancelling background agent jobs.

The POST /api/jobs endpoint returns immediately with a job ID
and queues the task for asynchronous processing by Celery.
"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import User
from app.auth.dependencies import get_current_active_user
from app.jobs.repository import JobRepository
from app.jobs.service import (
    JobService,
    JobNotFoundError,
    InvalidJobTransitionError,
    InvalidJobTypeError,
)
from app.schemas.jobs import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
    JobCancelResponse,
    JobListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])


def _get_service(session: AsyncSession) -> JobService:
    """Build the service with its repository from the injected session."""
    return JobService(JobRepository(session))


def _dispatch_celery_task(job_id: str) -> None:
    """Send the job to Celery for background processing.

    Wrapped in a function so it can be easily mocked in tests.
    If Celery/Redis is unavailable, the job remains pending and
    can be retried later.
    """
    try:
        from app.workers.tasks import run_agent_task
        run_agent_task.delay(job_id)
        logger.info("Dispatched job %s to Celery worker", job_id)
    except Exception as exc:
        logger.error(
            "Failed to dispatch job %s to Celery: %s. "
            "Job remains pending and can be retried when Celery is available.",
            job_id, exc,
        )


# ---------------------------------------------------------------------------
# POST /api/jobs — Create a background job
# ---------------------------------------------------------------------------

@router.post("/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job(
    request: JobCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new background job and return immediately.

    The job is queued for asynchronous processing. Use GET /api/jobs/{job_id}
    to check status and retrieve results.
    """
    service = _get_service(session)
    user_id = current_user.id

    try:
        job = await service.create_job(
            user_id=user_id,
            message=request.message,
            job_type=request.job_type,
        )
    except InvalidJobTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Dispatch to Celery (non-blocking — failure is logged, not raised)
    _dispatch_celery_task(job.id)

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
    )


# ---------------------------------------------------------------------------
# GET /api/jobs — List all jobs
# ---------------------------------------------------------------------------

@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all background jobs for the current user."""
    service = _get_service(session)
    jobs = await service.list_jobs(user_id=current_user.id)
    return JobListResponse(
        jobs=[
            JobStatusResponse(
                job_id=j.id,
                status=j.status,
                job_type=j.job_type,
                input=j.input,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                result=j.result,
                error=j.error,
            )
            for j in jobs
        ],
        total=len(jobs),
    )


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id} — Get job status
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the status and result of a background job."""
    service = _get_service(session)
    try:
        job = await service.get_job(job_id)
        if job.user_id != current_user.id:
            raise JobNotFoundError()
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        job_type=job.job_type,
        input=job.input,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        result=job.result,
        error=job.error,
    )


# ---------------------------------------------------------------------------
# POST /api/jobs/{job_id}/cancel — Cancel a pending job
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel a pending background job.

    Only jobs in 'pending' status can be cancelled.
    Running jobs cannot be safely interrupted.
    """
    service = _get_service(session)
    try:
        # Check ownership first
        job = await service.get_job(job_id)
        if job.user_id != current_user.id:
            raise JobNotFoundError()
        job = await service.cancel_job(job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    except InvalidJobTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return JobCancelResponse(
        job_id=job.id,
        status=job.status,
        message="Job has been cancelled.",
    )
