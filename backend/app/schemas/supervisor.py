"""
Pydantic schemas for the Supervisor Agent decision.
"""

from pydantic import BaseModel, Field


class SupervisorDecision(BaseModel):
    """Structured output from the Supervisor Agent's analysis of a user message."""

    intent: str = Field(
        ...,
        description="Classified intent: coding, debugging, learning, or general.",
    )
    complexity: str = Field(
        ...,
        description="Estimated complexity: simple, moderate, or complex.",
    )
    plan: list[str] = Field(
        ...,
        description="Ordered list of steps the LLM should follow to address the request.",
    )
