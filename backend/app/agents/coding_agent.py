"""
Coding Agent — Phase 3.

Handles programming and code-generation requests. Constructs specialized
system and user prompts that guide the LLM to produce well-structured
code solutions with explanations and edge-case coverage.
"""

from __future__ import annotations

from app.agents.base import AgentResult, BaseAgent
from app.schemas.supervisor import SupervisorDecision


class CodingAgent(BaseAgent):
    """Specialized agent for coding and programming tasks."""

    @property
    def name(self) -> str:
        return "CodingAgent"

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
            "You are DevAgent's Coding Specialist. "
            "You are an expert programmer who helps developers write, "
            "improve, and understand code.\n\n"
            "Guidelines:\n"
            "- Generate clean, well-structured code when appropriate.\n"
            "- Explain the solution clearly and concisely.\n"
            "- Mention important edge cases when relevant.\n"
            "- Respect the user's requested programming language.\n"
            "- Use proper code formatting with language-specific syntax highlighting.\n"
            "- Include brief inline comments for non-obvious logic.\n\n"
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
