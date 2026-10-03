"""
Chat API route — delegates LLM interaction to the service layer.

Phase 3: The Supervisor Agent analyzes the user's message, then the
Agent Router selects a Specialized Agent to construct the prompt.

Phase 4: Before the LLM call, the tool decision service checks whether
a tool (e.g. calculator) is needed. If so, the tool result is injected
into the prompt so the LLM can weave it into a natural response.

Phase 6: Before processing, the chat route checks whether the user's
message requests a protected action. If so, an approval request is
created and returned — the action is NOT executed until approved.

Phase 8: Each chat request is traced for observability — agent,
intent, complexity, LLM calls, tool usage, duration, and status.
Trace failures never break the main chat flow.
"""

import logging
import re

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.agents.supervisor import analyze as supervisor_analyze
from app.agents.router import get_agent_for_intent
from app.services.llm_service import get_llm_response, get_llm_response_with_prompts
from app.services.tool_service import decide_tool
from app.memory.repository import MemoryRepository
from app.memory.service import MemoryService
from app.hitl.repository import ApprovalRepository
from app.hitl.service import HumanApprovalService
from app.hitl.schemas import ApprovalResponse, HITLChatResponse
from app.observability.repository import TraceRepository
from app.observability.service import TraceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# ---------------------------------------------------------------------------
# Phase 6 — Protected action detection
# ---------------------------------------------------------------------------

# Patterns that signal a request for the demo protected action
_PROTECTED_ACTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?:run|execute|perform|trigger)\s+(?:the\s+)?(?:demo\s+protected|protected\s+demo|protected|demo)\s+action", re.IGNORECASE),
]


def _requires_approval(message: str) -> bool:
    """Check if the user's message requests a protected action."""
    for pattern in _PROTECTED_ACTION_PATTERNS:
        if pattern.search(message):
            return True
    return False


def _enrich_prompt_with_tool(user_prompt: str, tool_decision) -> str:
    """Append tool output to the user prompt when a tool was executed successfully."""
    if (
        tool_decision.tool_needed
        and tool_decision.tool_result
        and tool_decision.tool_result.success
    ):
        return (
            f"{user_prompt}\n\n"
            f"[Tool Result — {tool_decision.tool_name}]\n"
            f"Expression: {tool_decision.tool_input}\n"
            f"Result: {tool_decision.tool_result.result}\n"
            f"Use this result to answer the user's question naturally."
        )
    return user_prompt


@router.post("/chat", response_model=HITLChatResponse)
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_db)):
    """Accept a user message and return an AI-generated response."""

    message = request.message.strip()

    # Validate empty message
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Validate message length
    if len(message) > settings.MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message exceeds maximum length of {settings.MAX_MESSAGE_LENGTH} characters.",
        )

    user_id = "default-user"

    # ------------------------------------------------------------------
    # Phase 6 — Check if the message requires HITL approval
    # ------------------------------------------------------------------
    if _requires_approval(message):
        approval_repo = ApprovalRepository(session)
        approval_service = HumanApprovalService(approval_repo)

        approval = await approval_service.create_approval(
            user_id=user_id,
            action_type="demo_protected_action",
            description="Run the demo protected action — a safe simulated operation that demonstrates the Human-in-the-Loop approval workflow.",
        )

        return HITLChatResponse(
            response=(
                "⚠️ This action requires your approval before it can be executed.\n\n"
                f"**Action:** {approval.description}\n"
                f"**Approval ID:** {approval.id}\n"
                f"**Status:** {approval.status}\n\n"
                "Please approve or reject this request using the buttons below."
            ),
            requires_approval=True,
            approval=ApprovalResponse.model_validate(approval),
        )

    # ------------------------------------------------------------------
    # Phase 8 — Start execution trace
    # ------------------------------------------------------------------
    trace = None
    trace_service = None
    try:
        trace_repo = TraceRepository(session)
        trace_service = TraceService(trace_repo)
        trace = await trace_service.start_trace(user_id=user_id)
    except Exception as exc:
        logger.warning("Failed to start observability trace: %s", exc)

    # ------------------------------------------------------------------
    # Normal chat flow (Phase 1–7 unchanged)
    # ------------------------------------------------------------------

    # Initialize memory components
    memory_repo = MemoryRepository(session)
    memory_service = MemoryService(memory_repo)
    
    # Ensure conversation and extract new memory
    conv_id = await memory_service.ensure_conversation(user_id)
    await memory_service.save_message(conv_id, "user", message)
    await memory_service.extract_and_save_memory(user_id, message)

    # Phase 8 — Record conversation_id on trace
    if trace:
        try:
            trace.conversation_id = conv_id
        except Exception:
            pass
    
    # Retrieve relevant memory context
    relevant_memories = await memory_service.get_relevant_memories(user_id, message)
    memory_context = memory_service.format_memory_context(relevant_memories)

    # Phase 2 — Supervisor analysis (graceful fallback on failure)
    supervisor_decision = None
    try:
        supervisor_decision = await supervisor_analyze(message)
        # Phase 8 — Record intent and complexity
        if trace and trace_service and supervisor_decision:
            try:
                await trace_service.record_intent(
                    trace,
                    task_type=supervisor_decision.intent,
                    complexity=supervisor_decision.complexity,
                )
            except Exception as exc:
                logger.warning("Failed to record trace intent: %s", exc)
    except Exception as exc:
        logger.warning("Supervisor analysis failed, proceeding without it: %s", exc)

    # Phase 4 — Tool decision (graceful fallback on failure)
    tool_decision = None
    try:
        tool_decision = await decide_tool(message)
        if tool_decision.tool_needed:
            logger.info(
                "Tool '%s' executed — success=%s",
                tool_decision.tool_name,
                tool_decision.tool_result.success if tool_decision.tool_result else False,
            )
            # Phase 8 — Record tool call
            if trace and trace_service and tool_decision.tool_name:
                try:
                    await trace_service.record_tool_call(trace, tool_decision.tool_name)
                except Exception as exc:
                    logger.warning("Failed to record trace tool call: %s", exc)
    except Exception as exc:
        logger.warning("Tool decision failed, proceeding without tools: %s", exc)

    try:
        if supervisor_decision:
            # Phase 3 - Route to specialized agent if available
            agent = get_agent_for_intent(supervisor_decision.intent)
            if agent:
                # Phase 8 — Record agent name
                if trace and trace_service:
                    try:
                        await trace_service.record_agent(trace, agent.name)
                    except Exception:
                        pass

                agent_result = await agent.handle(message, supervisor_decision)
                # Phase 4 — enrich prompt with tool result if applicable
                enriched_prompt = (
                    _enrich_prompt_with_tool(agent_result.user_prompt, tool_decision)
                    if tool_decision
                    else agent_result.user_prompt
                )
                if memory_context:
                    enriched_prompt = f"{enriched_prompt}\n{memory_context}"
                response_text = await get_llm_response_with_prompts(
                    system_prompt=agent_result.system_prompt,
                    user_prompt=enriched_prompt,
                )
            else:
                # No specialized agent (e.g., general intent)
                # Phase 8 — Record agent as "general"
                if trace and trace_service:
                    try:
                        await trace_service.record_agent(trace, "general")
                    except Exception:
                        pass

                enriched_message = (
                    _enrich_prompt_with_tool(message, tool_decision)
                    if tool_decision
                    else message
                )
                if memory_context:
                    enriched_message = f"{enriched_message}\n{memory_context}"
                response_text = await get_llm_response(
                    enriched_message, supervisor_context=supervisor_decision
                )
        else:
            # Fallback when supervisor fails
            enriched_message = (
                _enrich_prompt_with_tool(message, tool_decision)
                if tool_decision
                else message
            )
            if memory_context:
                enriched_message = f"{enriched_message}\n{memory_context}"
            response_text = await get_llm_response(
                enriched_message, supervisor_context=None
            )

        # Phase 8 — Record LLM call (one call per chat request)
        if trace and trace_service:
            try:
                await trace_service.record_llm_call(trace)
            except Exception as exc:
                logger.warning("Failed to record trace LLM call: %s", exc)

        # Save assistant response
        await memory_service.save_message(conv_id, "assistant", response_text)

        # Phase 8 — Complete trace
        if trace and trace_service:
            try:
                await trace_service.complete_trace(trace)
            except Exception as exc:
                logger.warning("Failed to complete observability trace: %s", exc)

        return HITLChatResponse(response=response_text)

    except TimeoutError:
        logger.error("LLM request timed out.")
        # Phase 8 — Record failure
        if trace and trace_service:
            try:
                await trace_service.fail_trace(trace, "LLM request timed out")
            except Exception:
                pass
        raise HTTPException(
            status_code=504,
            detail="The AI service took too long to respond. Please try again.",
        )

    except ConnectionError as exc:
        logger.error("LLM service connection error: %s", exc)
        # Phase 8 — Record failure
        if trace and trace_service:
            try:
                await trace_service.fail_trace(trace, "Cannot connect to LLM service")
            except Exception:
                pass
        raise HTTPException(
            status_code=503,
            detail="Unable to reach the AI service. Please try again later.",
        )

    except Exception as exc:
        logger.error("Unexpected error in chat endpoint: %s", exc)
        # Phase 8 — Record failure
        if trace and trace_service:
            try:
                await trace_service.fail_trace(trace, "An unexpected error occurred")
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        )
