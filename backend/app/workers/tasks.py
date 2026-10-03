"""
Celery tasks — Phase 7 + Phase 8 Observability.

Background tasks that reuse the existing agent workflow.
The worker runs the Supervisor → Agent Router → Specialized Agent
→ Tool Service → Memory Service → LLM Service pipeline and stores
the result in the database.

Phase 8 adds execution tracing: each background job execution is
recorded in the ExecutionTrace table with agent, intent, tool, and
LLM call metrics.
"""

import json
import logging
import asyncio
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.workers.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synchronous database session for Celery workers.
# Celery tasks run synchronously, so we use a regular (non-async) engine.
# ---------------------------------------------------------------------------

_SYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "sqlite+aiosqlite", "sqlite"
).replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
)

_sync_engine = create_engine(_SYNC_DATABASE_URL, echo=False)
_SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)


def _get_sync_session() -> Session:
    """Return a synchronous database session for use in Celery tasks."""
    return _SyncSession()


# ---------------------------------------------------------------------------
# Phase 8 — Synchronous trace helpers for Celery workers
# ---------------------------------------------------------------------------

def _start_trace_sync(session: Session, user_id: str, job_id: str) -> "ExecutionTrace | None":
    """Create a new execution trace synchronously."""
    try:
        from app.database.models import ExecutionTrace
        trace = ExecutionTrace(
            user_id=user_id,
            job_id=job_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        session.add(trace)
        session.commit()
        session.refresh(trace)
        return trace
    except Exception as exc:
        logger.warning("Failed to start trace for job %s: %s", job_id, exc)
        return None


def _record_trace_intent_sync(
    session: Session,
    trace,
    task_type: str,
    complexity: str | None = None,
) -> None:
    """Record intent and complexity on a trace synchronously."""
    try:
        trace.task_type = task_type
        if complexity:
            trace.complexity = complexity
        session.commit()
    except Exception as exc:
        logger.warning("Failed to record trace intent: %s", exc)


def _record_trace_agent_sync(session: Session, trace, agent_name: str) -> None:
    """Record agent name on a trace synchronously."""
    try:
        trace.agent_name = agent_name
        session.commit()
    except Exception as exc:
        logger.warning("Failed to record trace agent: %s", exc)


def _record_trace_llm_call_sync(session: Session, trace) -> None:
    """Increment LLM call count on a trace synchronously."""
    try:
        trace.llm_call_count += 1
        session.commit()
    except Exception as exc:
        logger.warning("Failed to record trace LLM call: %s", exc)


def _record_trace_tool_call_sync(session: Session, trace, tool_name: str) -> None:
    """Record a tool call on a trace synchronously."""
    try:
        trace.tool_call_count += 1
        tools = trace.get_tools_used()
        if tool_name not in tools:
            tools.append(tool_name)
        trace.set_tools_used(tools)
        session.commit()
    except Exception as exc:
        logger.warning("Failed to record trace tool call: %s", exc)


def _complete_trace_sync(session: Session, trace) -> None:
    """Mark trace as completed synchronously."""
    try:
        trace.status = "completed"
        trace.completed_at = datetime.utcnow()
        delta = trace.completed_at - trace.started_at
        trace.duration_ms = round(delta.total_seconds() * 1000, 2)
        session.commit()
    except Exception as exc:
        logger.warning("Failed to complete trace: %s", exc)


def _fail_trace_sync(session: Session, trace, error_message: str) -> None:
    """Mark trace as failed synchronously."""
    try:
        trace.status = "failed"
        trace.completed_at = datetime.utcnow()
        delta = trace.completed_at - trace.started_at
        trace.duration_ms = round(delta.total_seconds() * 1000, 2)
        trace.error_message = (error_message[:500] if error_message else "Unknown error")
        session.commit()
    except Exception as exc:
        logger.warning("Failed to record trace failure: %s", exc)


# ---------------------------------------------------------------------------
# Helper: run the existing async agent pipeline synchronously
# ---------------------------------------------------------------------------

def _run_agent_pipeline(user_message: str, session: Session = None, trace=None) -> str:
    """Execute the full async agent pipeline synchronously.

    Reuses the existing:
    - Supervisor (analyze)
    - Agent Router (get_agent_for_intent)
    - Specialized Agents (CodingAgent, DebuggingAgent, StudyAgent)
    - Tool Service (decide_tool)
    - LLM Service (get_llm_response, get_llm_response_with_prompts)

    Does NOT create duplicate LLM clients or agents.
    """
    async def _async_pipeline() -> str:
        from app.agents.supervisor import analyze as supervisor_analyze
        from app.agents.router import get_agent_for_intent
        from app.services.llm_service import get_llm_response, get_llm_response_with_prompts
        from app.services.tool_service import decide_tool

        # Phase 2 — Supervisor analysis
        supervisor_decision = None
        try:
            supervisor_decision = await supervisor_analyze(user_message)
            # Phase 8 — Record intent
            if trace and session and supervisor_decision:
                _record_trace_intent_sync(
                    session, trace,
                    task_type=supervisor_decision.intent,
                    complexity=supervisor_decision.complexity,
                )
        except Exception as exc:
            logger.warning("Supervisor analysis failed in worker: %s", exc)

        # Phase 4 — Tool decision
        tool_decision = None
        try:
            tool_decision = await decide_tool(user_message)
            # Phase 8 — Record tool call
            if tool_decision.tool_needed and tool_decision.tool_name and trace and session:
                _record_trace_tool_call_sync(session, trace, tool_decision.tool_name)
        except Exception as exc:
            logger.warning("Tool decision failed in worker: %s", exc)

        def _enrich_with_tool(prompt: str) -> str:
            """Append tool result to prompt if a tool was executed."""
            if (
                tool_decision
                and tool_decision.tool_needed
                and tool_decision.tool_result
                and tool_decision.tool_result.success
            ):
                return (
                    f"{prompt}\n\n"
                    f"[Tool Result — {tool_decision.tool_name}]\n"
                    f"Expression: {tool_decision.tool_input}\n"
                    f"Result: {tool_decision.tool_result.result}\n"
                    f"Use this result to answer the user's question naturally."
                )
            return prompt

        result_text = None
        if supervisor_decision:
            agent = get_agent_for_intent(supervisor_decision.intent)
            if agent:
                # Phase 8 — Record agent
                if trace and session:
                    _record_trace_agent_sync(session, trace, agent.name)

                agent_result = await agent.handle(user_message, supervisor_decision)
                enriched_prompt = _enrich_with_tool(agent_result.user_prompt)
                result_text = await get_llm_response_with_prompts(
                    system_prompt=agent_result.system_prompt,
                    user_prompt=enriched_prompt,
                )
            else:
                # Phase 8 — Record general agent
                if trace and session:
                    _record_trace_agent_sync(session, trace, "general")

                enriched_message = _enrich_with_tool(user_message)
                result_text = await get_llm_response(
                    enriched_message, supervisor_context=supervisor_decision
                )
        else:
            enriched_message = _enrich_with_tool(user_message)
            result_text = await get_llm_response(
                enriched_message, supervisor_context=None
            )

        # Phase 8 — Record LLM call
        if trace and session:
            _record_trace_llm_call_sync(session, trace)

        return result_text

    # Run the async pipeline in a new event loop (Celery workers are sync)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_async_pipeline())
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Celery Task: agent_task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="devagent.agent_task", max_retries=0)
def run_agent_task(self, job_id: str) -> dict:
    """Execute the agent workflow for a background job.

    Lifecycle:
        1. Mark job RUNNING
        2. Start execution trace (Phase 8)
        3. Run Supervisor → Agent Router → Specialized Agent → LLM
        4. Store result
        5. Mark job COMPLETED (or FAILED on exception)
        6. Complete/fail trace (Phase 8)

    Args:
        job_id: The database Job ID to process.

    Returns:
        A dict with the job result summary.
    """
    from app.database.models import Job

    session = _get_sync_session()
    trace = None
    try:
        # Fetch the job
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("Job %s not found in database", job_id)
            return {"error": "Job not found"}

        # Check for cancellation before starting
        if job.status == "cancelled":
            logger.info("Job %s was cancelled before starting", job_id)
            return {"status": "cancelled"}

        # Transition: pending → running
        if job.status != "pending":
            logger.warning("Job %s has unexpected status '%s', skipping", job_id, job.status)
            return {"error": f"Unexpected job status: {job.status}"}

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        session.commit()

        logger.info("Job %s started — running agent pipeline", job_id)

        # Phase 8 — Start execution trace
        trace = _start_trace_sync(session, user_id=job.user_id, job_id=job_id)

        # Execute the agent pipeline (with trace context)
        result_text = _run_agent_pipeline(job.input, session=session, trace=trace)

        # Mark completed
        job.status = "completed"
        job.result = result_text
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        session.commit()

        # Phase 8 — Complete trace
        if trace:
            _complete_trace_sync(session, trace)

        logger.info("Job %s completed successfully", job_id)
        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        # Mark failed — never expose raw stack traces
        logger.error("Job %s failed: %s", job_id, exc)

        # Phase 8 — Fail trace
        if trace:
            _fail_trace_sync(session, trace, "An error occurred while processing this task")

        try:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job and job.status in ("pending", "running"):
                job.status = "failed"
                job.error = "An error occurred while processing this task. Please try again."
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                session.commit()
        except Exception as db_exc:
            logger.error("Failed to update job %s status to failed: %s", job_id, db_exc)

        return {"status": "failed", "job_id": job_id, "error": str(exc)}

    finally:
        session.close()
