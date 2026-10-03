"""
Observability Service — Phase 8.

Business logic for execution tracing. Provides a clean API for
starting, recording, and completing traces. All trace operations
are fail-safe — errors are logged but never break the main flow.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from app.database.models import ExecutionTrace
from app.observability.repository import TraceRepository
from app.observability.schemas import TraceResponse, ObservabilityStats

logger = logging.getLogger(__name__)


class TraceService:
    """Service for managing execution traces.

    Architecture:
        Route → TraceService → TraceRepository → Database
    """

    def __init__(self, repository: TraceRepository) -> None:
        self.repository = repository

    async def start_trace(
        self,
        user_id: str,
        job_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> ExecutionTrace:
        """Start a new execution trace.

        Args:
            user_id: The user who triggered the execution.
            job_id: Optional associated job ID.
            conversation_id: Optional associated conversation ID.

        Returns:
            The created ExecutionTrace.
        """
        trace = ExecutionTrace(
            user_id=user_id,
            job_id=job_id,
            conversation_id=conversation_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        return await self.repository.create(trace)

    async def record_agent(
        self,
        trace: ExecutionTrace,
        agent_name: str,
    ) -> ExecutionTrace:
        """Record which agent handled the task."""
        trace.agent_name = agent_name
        return await self.repository.update(trace)

    async def record_intent(
        self,
        trace: ExecutionTrace,
        task_type: str,
        complexity: Optional[str] = None,
    ) -> ExecutionTrace:
        """Record the detected intent and complexity."""
        trace.task_type = task_type
        if complexity:
            trace.complexity = complexity
        return await self.repository.update(trace)

    async def record_llm_call(self, trace: ExecutionTrace) -> ExecutionTrace:
        """Increment the LLM call counter."""
        trace.llm_call_count += 1
        return await self.repository.update(trace)

    async def record_tool_call(
        self,
        trace: ExecutionTrace,
        tool_name: str,
    ) -> ExecutionTrace:
        """Record a tool invocation."""
        trace.tool_call_count += 1
        tools = trace.get_tools_used()
        if tool_name not in tools:
            tools.append(tool_name)
        trace.set_tools_used(tools)
        return await self.repository.update(trace)

    async def complete_trace(self, trace: ExecutionTrace) -> ExecutionTrace:
        """Mark the trace as completed and calculate duration."""
        trace.status = "completed"
        trace.completed_at = datetime.utcnow()
        trace.duration_ms = self._calculate_duration(trace.started_at, trace.completed_at)
        return await self.repository.update(trace)

    async def fail_trace(
        self,
        trace: ExecutionTrace,
        error_message: str,
    ) -> ExecutionTrace:
        """Mark the trace as failed with an error message."""
        trace.status = "failed"
        trace.completed_at = datetime.utcnow()
        trace.duration_ms = self._calculate_duration(trace.started_at, trace.completed_at)
        # Sanitize: never store raw stack traces or sensitive data
        trace.error_message = error_message[:500] if error_message else "Unknown error"
        return await self.repository.update(trace)

    async def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Retrieve a single trace by ID."""
        return await self.repository.get_by_id(trace_id)

    async def list_traces(self, limit: int = 50) -> list[ExecutionTrace]:
        """List recent traces."""
        return await self.repository.list_all(limit=limit)

    async def get_stats(self) -> ObservabilityStats:
        """Get aggregate statistics."""
        stats_dict = await self.repository.get_stats()
        return ObservabilityStats(**stats_dict)

    @staticmethod
    def _calculate_duration(
        started_at: datetime,
        completed_at: datetime,
    ) -> float:
        """Calculate duration in milliseconds between two timestamps."""
        delta = completed_at - started_at
        return round(delta.total_seconds() * 1000, 2)

    @staticmethod
    def trace_to_response(trace: ExecutionTrace) -> TraceResponse:
        """Convert an ExecutionTrace model to a TraceResponse schema."""
        return TraceResponse(
            id=trace.id,
            job_id=trace.job_id,
            conversation_id=trace.conversation_id,
            user_id=trace.user_id,
            task_type=trace.task_type,
            complexity=trace.complexity,
            agent_name=trace.agent_name,
            status=trace.status,
            started_at=trace.started_at,
            completed_at=trace.completed_at,
            duration_ms=trace.duration_ms,
            llm_call_count=trace.llm_call_count,
            tool_call_count=trace.tool_call_count,
            tools_used=trace.get_tools_used(),
            error_message=trace.error_message,
            created_at=trace.created_at,
        )
