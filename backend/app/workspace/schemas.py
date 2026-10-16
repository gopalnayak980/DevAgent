"""
Pydantic schemas for workspaces — Phase 11.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class WorkspaceCreateRequest(BaseModel):
    """Request body to create a workspace."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Human-readable workspace name.",
    )
    root_path: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Relative path under the workspace root directory.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class WorkspaceResponse(BaseModel):
    """Workspace details returned to the client."""

    id: str = Field(..., description="Unique workspace identifier.")
    user_id: str = Field(..., description="Owner's user identifier.")
    name: str = Field(..., description="Human-readable workspace name.")
    root_path: str = Field(..., description="Resolved path within the allowed workspace root.")
    created_at: datetime = Field(..., description="When the workspace was created.")
    updated_at: datetime = Field(..., description="When the workspace was last updated.")

    model_config = {"from_attributes": True}


class WorkspaceListResponse(BaseModel):
    """List of workspaces."""

    workspaces: list[WorkspaceResponse] = Field(..., description="List of workspaces.")
    total: int = Field(..., description="Total number of workspaces returned.")


# ---------------------------------------------------------------------------
# Phase 11.3 — File schemas
# ---------------------------------------------------------------------------


class FileEntry(BaseModel):
    """A single file or directory entry within a workspace."""

    name: str = Field(..., description="Entry filename or directory name.")
    path: str = Field(..., description="Workspace-relative path (never absolute).")
    type: str = Field(..., description="'file' or 'directory'.")
    size: int | None = Field(None, description="File size in bytes (files only).")


class FileListResponse(BaseModel):
    """Structured directory listing for a workspace path."""

    workspace_id: str = Field(..., description="Workspace identifier.")
    path: str = Field(..., description="The listed workspace-relative directory path.")
    files: list[FileEntry] = Field(..., description="Regular files in this directory.")
    directories: list[FileEntry] = Field(..., description="Subdirectories in this directory.")


class FileContentResponse(BaseModel):
    """Content of a single file within a workspace."""

    workspace_id: str = Field(..., description="Workspace identifier.")
    path: str = Field(..., description="Workspace-relative path of the file.")
    content: str = Field(..., description="UTF-8 text content of the file.")
    size: int = Field(..., description="File size in bytes.")
    language: str = Field(..., description="Detected programming/markup language.")


# ---------------------------------------------------------------------------
# Phase 11.4 — Safe File Modification + Human Approval Schemas
# ---------------------------------------------------------------------------


class FileChangeProposalCreateRequest(BaseModel):
    """Request body to propose a file change."""

    file_path: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Workspace-relative file path (e.g. 'src/App.jsx').",
    )
    proposed_content: str = Field(
        ...,
        description="Complete proposed UTF-8 text content for the file.",
    )


class FileChangeProposalResponse(BaseModel):
    """Details of a file change proposal."""

    id: str = Field(..., description="Unique proposal identifier.")
    workspace_id: str = Field(..., description="Workspace identifier.")
    user_id: str = Field(..., description="Owner's user identifier.")
    file_path: str = Field(..., description="Workspace-relative file path.")
    original_content_hash: str = Field(..., description="SHA-256 hash of original file content.")
    proposed_content_hash: str = Field(..., description="SHA-256 hash of proposed file content.")
    original_content: str = Field(..., description="Original file content when proposal was created.")
    proposed_content: str = Field(..., description="Proposed file content.")
    diff: str = Field(..., description="Exact unified diff representation.")
    status: str = Field(..., description="Proposal status: pending, approved, rejected, applied, failed, cancelled.")
    created_at: datetime = Field(..., description="When the proposal was created.")
    updated_at: datetime = Field(..., description="When the proposal was last updated.")
    approved_at: datetime | None = Field(None, description="When the proposal was approved.")
    rejected_at: datetime | None = Field(None, description="When the proposal was rejected.")
    applied_at: datetime | None = Field(None, description="When the proposal was applied to disk.")

    model_config = {"from_attributes": True}


class FileChangeProposalListResponse(BaseModel):
    """List of file change proposals."""

    proposals: list[FileChangeProposalResponse] = Field(..., description="List of proposals.")
    total: int = Field(..., description="Total count.")

