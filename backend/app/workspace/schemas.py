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
