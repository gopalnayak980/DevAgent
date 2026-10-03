"""
Study Agent — Phase 3.

Handles learning, educational, and exam-preparation requests. Constructs
specialized system and user prompts that guide the LLM to explain concepts
clearly with examples and structured formatting.
"""

from __future__ import annotations

from app.agents.base import AgentResult, BaseAgent
from app.schemas.supervisor import SupervisorDecision


class StudyAgent(BaseAgent):
    """Specialized agent for learning and educational tasks."""

    @property
    def name(self) -> str:
        return "StudyAgent"

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
            "You are DevAgent's Study & Learning Specialist. "
            "You are an expert educator who helps users understand "
            "programming concepts, computer science topics, and "
            "software engineering principles.\n\n"
            "Guidelines:\n"
            "- Explain concepts clearly and accurately.\n"
            "- Use simple language when appropriate, avoiding unnecessary jargon.\n"
            "- Provide concrete examples to illustrate ideas.\n"
            "- Structure explanations with headings, bullet points, "
            "or numbered steps when useful.\n"
            "- Build understanding progressively — start with fundamentals "
            "before diving into advanced details.\n"
            "- When comparing concepts, use clear side-by-side comparisons.\n\n"
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
