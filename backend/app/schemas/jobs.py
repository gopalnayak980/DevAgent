"""
Pydantic schemas for background jobs — Phase 7.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class JobCreateRequest(BaseModel):
    """Request body to create a background job."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The user's task to process in the background.",
    )
    job_type: str = Field(
        default="agent_task",
        description="Type of background job. Currently only 'agent_task' is supported.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class JobCreateResponse(BaseModel):
    """Response after creating a background job."""

    job_id: str = Field(..., description="Unique job identifier.")
    status: str = Field(..., description="Initial job status (pending).")


class JobStatusResponse(BaseModel):
    """Full job status response."""

    job_id: str = Field(..., description="Unique job identifier.")
    status: str = Field(..., description="Current status: pending, running, completed, failed, cancelled.")
    job_type: str = Field(..., description="Type of background job.")
    input: str = Field(..., description="The original task input.")
    created_at: datetime = Field(..., description="When the job was created.")
    started_at: Optional[datetime] = Field(None, description="When the job started executing.")
    completed_at: Optional[datetime] = Field(None, description="When the job finished.")
    result: Optional[str] = Field(None, description="The job result, if completed.")
    error: Optional[str] = Field(None, description="Error message, if failed.")

    model_config = {"from_attributes": True}


class JobCancelResponse(BaseModel):
    """Response after cancelling a job."""

    job_id: str = Field(..., description="Unique job identifier.")
    status: str = Field(..., description="Updated job status.")
    message: str = Field(..., description="Human-readable result message.")


class JobListResponse(BaseModel):
    """List of jobs."""

    jobs: list[JobStatusResponse] = Field(..., description="List of jobs.")
    total: int = Field(..., description="Total number of jobs returned.")
