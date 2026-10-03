"""
Base abstractions for specialized agents — Phase 3.

Provides:
- AgentResult: Pydantic model for the output of any specialized agent.
- BaseAgent: Abstract base class that all specialized agents implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.schemas.supervisor import SupervisorDecision


class AgentResult(BaseModel):
    """Structured output from a specialized agent.

    Contains the system prompt and user prompt that should be sent
    to the LLM service. The agent does NOT call the LLM itself — it
    only prepares the instructions.
    """

    agent_name: str = Field(
        ...,
        description="Name of the agent that produced this result.",
    )
    system_prompt: str = Field(
        ...,
        description="The full system prompt to send to the LLM.",
    )
    user_prompt: str = Field(
        ...,
        description="The user prompt to send to the LLM (may be enriched by the agent).",
    )


class BaseAgent(ABC):
    """Abstract base class for specialized agents.

    Each agent is responsible for constructing tailored prompts
    for the LLM service based on the user's message and the
    supervisor's analysis. Agents must NOT create their own LLM
    clients — the LLM service remains the single provider abstraction.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this agent."""

    @abstractmethod
    async def handle(
        self,
        user_message: str,
        supervisor_decision: SupervisorDecision,
    ) -> AgentResult:
        """Prepare prompts for the LLM based on the user's message.

        Args:
            user_message: The raw message from the user.
            supervisor_decision: The supervisor's intent/complexity/plan analysis.

        Returns:
            An AgentResult with tailored system and user prompts.
        """
