"""
Pydantic schemas for Human-in-the-Loop approval requests — Phase 6.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ApprovalCreateRequest(BaseModel):
    """Request body to create a new approval request."""

    action_type: str = Field(
        ...,
        min_length=1,
        description="Identifier for the type of action requiring approval.",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the action.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ApprovalResponse(BaseModel):
    """Single approval request returned to the client."""

    id: str = Field(..., description="Unique identifier for the approval request.")
    user_id: str = Field(..., description="User who triggered the approval.")
    action_type: str = Field(..., description="Type of action requiring approval.")
    description: str = Field(..., description="Description of the action.")
    status: str = Field(..., description="Current status: pending, approved, rejected, cancelled.")
    created_at: datetime = Field(..., description="When the request was created.")
    updated_at: datetime = Field(..., description="When the request was last modified.")
    resolved_at: Optional[datetime] = Field(None, description="When the request was resolved.")

    model_config = {"from_attributes": True}


class ApprovalListResponse(BaseModel):
    """List of approval requests."""

    approvals: list[ApprovalResponse] = Field(
        ...,
        description="List of approval requests.",
    )
    total: int = Field(..., description="Total number of approvals returned.")


class ApprovalActionResponse(BaseModel):
    """Response after an approval action (approve/reject/cancel)."""

    id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Chat integration schemas
# ---------------------------------------------------------------------------

class HITLChatResponse(BaseModel):
    """Extended chat response when an approval is required."""

    response: str = Field(
        ...,
        description="The AI assistant's response explaining the approval requirement.",
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether the response requires human approval.",
    )
    approval: Optional[ApprovalResponse] = Field(
        default=None,
        description="The approval request details, if approval is required.",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="The ID of the active conversation.",
    )
