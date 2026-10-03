"""
Observability Repository — Phase 8.

Data access layer for execution traces. All database interactions
go through this repository. The service layer handles business logic.
"""

from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ExecutionTrace


class TraceRepository:
    """Repository for ExecutionTrace CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, trace: ExecutionTrace) -> ExecutionTrace:
        """Persist a new execution trace."""
        self.session.add(trace)
        await self.session.commit()
        await self.session.refresh(trace)
        return trace

    async def get_by_id(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Retrieve a single trace by ID."""
        result = await self.session.execute(
            select(ExecutionTrace).where(ExecutionTrace.id == trace_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50, user_id: Optional[str] = None) -> List[ExecutionTrace]:
        """List recent traces, ordered by created_at descending."""
        stmt = select(ExecutionTrace).order_by(ExecutionTrace.created_at.desc())
        if user_id:
            stmt = stmt.where(ExecutionTrace.user_id == user_id)
        stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, trace: ExecutionTrace) -> ExecutionTrace:
        """Update an existing trace."""
        await self.session.commit()
        await self.session.refresh(trace)
        return trace

    async def get_stats(self, user_id: Optional[str] = None) -> dict:
        """Compute aggregate statistics across all traces."""
        def apply_filter(stmt):
            if user_id:
                return stmt.where(ExecutionTrace.user_id == user_id)
            return stmt

        total_result = await self.session.execute(
            apply_filter(select(func.count(ExecutionTrace.id)))
        )
        total = total_result.scalar() or 0

        success_result = await self.session.execute(
            apply_filter(select(func.count(ExecutionTrace.id)).where(
                ExecutionTrace.status == "completed"
            ))
        )
        successful = success_result.scalar() or 0

        failed_result = await self.session.execute(
            apply_filter(select(func.count(ExecutionTrace.id)).where(
                ExecutionTrace.status == "failed"
            ))
        )
        failed = failed_result.scalar() or 0

        avg_duration_result = await self.session.execute(
            apply_filter(select(func.avg(ExecutionTrace.duration_ms)).where(
                ExecutionTrace.duration_ms.isnot(None)
            ))
        )
        avg_duration = avg_duration_result.scalar()

        llm_calls_result = await self.session.execute(
            apply_filter(select(func.sum(ExecutionTrace.llm_call_count)))
        )
        total_llm_calls = llm_calls_result.scalar() or 0

        tool_calls_result = await self.session.execute(
            apply_filter(select(func.sum(ExecutionTrace.tool_call_count)))
        )
        total_tool_calls = tool_calls_result.scalar() or 0

        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "average_duration_ms": round(avg_duration, 2) if avg_duration else None,
            "total_llm_calls": total_llm_calls,
            "total_tool_calls": total_tool_calls,
        }
