"""
Debugging Agent — Phase 3.

Handles debugging and error-resolution requests. Constructs specialized
system and user prompts that guide the LLM to analyze problems, identify
root causes, and provide clear fixes.
"""

from __future__ import annotations

from app.agents.base import AgentResult, BaseAgent
from app.schemas.supervisor import SupervisorDecision


class DebuggingAgent(BaseAgent):
    """Specialized agent for debugging and error-related tasks."""

    @property
    def name(self) -> str:
        return "DebuggingAgent"

    async def handle(
        self,
        user_message: str,
        supervisor_decision: SupervisorDecision,
    ) -> AgentResult:
        plan_text = "\n".join(
            f"  {i + 1}. {step}"
            for i, step in enumerate(supervisor_decision.plan)
        )

        system_prompt = (
            "You are DevAgent's Debugging Specialist. "
            "You are an expert at diagnosing and resolving software bugs, "
            "errors, and unexpected behavior.\n\n"
            "Guidelines:\n"
            "- Analyze the reported problem carefully.\n"
            "- Explain the likely root cause clearly.\n"
            "- Provide a fix or step-by-step debugging approach.\n"
            "- If the user hasn't shared enough code or error details, "
            "ask for the missing information.\n"
            "- When providing a fix, explain why it works.\n"
            "- Suggest preventive practices when relevant.\n\n"
            f"--- Supervisor Guidance ---\n"
            f"Intent: {supervisor_decision.intent}\n"
            f"Complexity: {supervisor_decision.complexity}\n"
            f"Plan:\n{plan_text}\n"
            f"Follow the plan above to structure your response."
        )

        return AgentResult(
            agent_name=self.name,
            system_prompt=system_prompt,
            user_prompt=user_message,
        )
