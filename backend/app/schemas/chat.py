"""
Pydantic schemas for the chat API.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str = Field(
        ...,
        min_length=1,
        description="The user's message to the AI assistant.",
    )


class ChatResponse(BaseModel):
    """AI-generated response returned to the user."""

    response: str = Field(
        ...,
        description="The AI assistant's response.",
    )
