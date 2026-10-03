"""
Pydantic schemas for observability and evaluation — Phase 8.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Trace response schemas
# ---------------------------------------------------------------------------

class TraceResponse(BaseModel):
    """Single execution trace returned to the client."""

    id: str = Field(..., description="Unique trace identifier.")
    job_id: Optional[str] = Field(None, description="Associated job ID, if any.")
    conversation_id: Optional[str] = Field(None, description="Associated conversation ID, if any.")
    user_id: str = Field(..., description="User who triggered the execution.")
    task_type: Optional[str] = Field(None, description="Detected intent/task type.")
    complexity: Optional[str] = Field(None, description="Detected complexity.")
    agent_name: Optional[str] = Field(None, description="Agent that handled the task.")
    status: str = Field(..., description="Execution status: running, completed, failed.")
    started_at: datetime = Field(..., description="When execution started.")
    completed_at: Optional[datetime] = Field(None, description="When execution completed.")
    duration_ms: Optional[float] = Field(None, description="Execution duration in milliseconds.")
    llm_call_count: int = Field(0, description="Number of LLM calls made.")
    tool_call_count: int = Field(0, description="Number of tool calls made.")
    tools_used: list[str] = Field(default_factory=list, description="List of tool names used.")
    error_message: Optional[str] = Field(None, description="Error message, if failed.")
    created_at: datetime = Field(..., description="When the trace was created.")

    model_config = {"from_attributes": True}


class TraceListResponse(BaseModel):
    """List of execution traces."""

    traces: list[TraceResponse] = Field(..., description="List of traces.")
    total: int = Field(..., description="Total number of traces returned.")


class ObservabilityStats(BaseModel):
    """Aggregate statistics for observability."""

    total_executions: int = Field(0, description="Total number of executions recorded.")
    successful_executions: int = Field(0, description="Number of successful executions.")
    failed_executions: int = Field(0, description="Number of failed executions.")
    average_duration_ms: Optional[float] = Field(None, description="Average execution duration in milliseconds.")
    total_llm_calls: int = Field(0, description="Total number of LLM calls across all executions.")
    total_tool_calls: int = Field(0, description="Total number of tool calls across all executions.")
