"""
Pydantic schemas for the chat API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str = Field(
        ...,
        min_length=1,
        description="The user's message to the AI assistant.",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional ID of an existing conversation.",
    )

class ChatResponse(BaseModel):
    """AI-generated response returned to the user."""
    response: str = Field(
        ...,
        description="The AI assistant's response.",
    )

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    
    model_config = {"from_attributes": True}

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
