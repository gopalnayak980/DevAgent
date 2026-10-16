"""
Workspace API Routes — Phase 11: Code Workspace & Safe File Tools.

POST /api/workspaces                              — Create a new workspace.
GET  /api/workspaces                              — List current user's workspaces.
GET  /api/workspaces/{id}                         — Get a specific workspace by ID.
GET  /api/workspaces/{id}/files                   — List files in a workspace directory.
GET  /api/workspaces/{id}/files/content           — Read a file within a workspace.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import User
from app.auth.dependencies import get_current_active_user
from app.workspace.repository import WorkspaceRepository
from app.workspace.service import (
    WorkspaceService,
    WorkspaceNotFoundError,
    WorkspaceAccessDeniedError,
    InvalidWorkspacePathError,
    DuplicateWorkspaceNameError,
)
from app.workspace.file_service import (
    WorkspaceFileService,
    PathTraversalError,
    FileNotFoundInWorkspaceError,
    IsADirectoryError,
    FileTooLargeError,
    FileEncodingError,
)
from app.workspace.schemas import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceListResponse,
    FileListResponse,
    FileContentResponse,
    FileEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workspaces"])


def _get_service(session: AsyncSession) -> WorkspaceService:
    """Build the service with its repository from the injected session."""
    return WorkspaceService(WorkspaceRepository(session))


# ---------------------------------------------------------------------------
# POST /api/workspaces — Create a workspace
# ---------------------------------------------------------------------------

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new workspace for the authenticated user.

    - Workspace name must be unique per user.
    - Workspace path must be within the allowed workspace root directory.
    - Path traversal is not permitted.
    """
    service = _get_service(session)
    try:
        workspace = await service.create_workspace(
            user_id=current_user.id,
            name=request.name,
            root_path=request.root_path,
        )
    except InvalidWorkspacePathError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DuplicateWorkspaceNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return WorkspaceResponse.model_validate(workspace)


# ---------------------------------------------------------------------------
# GET /api/workspaces — List current user's workspaces
# ---------------------------------------------------------------------------

@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all workspaces owned by the authenticated user."""
    service = _get_service(session)
    workspaces = await service.list_workspaces(user_id=current_user.id)
    return WorkspaceListResponse(
        workspaces=[
            WorkspaceResponse.model_validate(w) for w in workspaces
        ],
        total=len(workspaces),
    )


# ---------------------------------------------------------------------------
# GET /api/workspaces/{workspace_id} — Get a workspace
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/files/content", response_model=FileContentResponse)
async def read_file(
    workspace_id: str,
    path: str = Query(..., description="Workspace-relative file path, e.g. 'src/App.jsx'."),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Read the content of a file within a workspace.

    - Enforces workspace ownership.
    - Validates path remains inside the workspace root.
    - Limits file size to 1 MB.
    - Decodes file as UTF-8.
    - Returns detected language based on file extension.
    - Absolute filesystem paths are never returned.

    Returns 400 for path traversal or directory paths.
    Returns 404 for non-existent files.
    Returns 413 for oversized files.
    Returns 422 for non-UTF-8 binary files.
    """
    ws_service = _get_service(session)
    try:
        workspace = await ws_service.get_workspace(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except (WorkspaceNotFoundError, WorkspaceAccessDeniedError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    file_service = WorkspaceFileService(workspace)
    try:
        result = file_service.read_file(path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except IsADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileNotFoundInWorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )
    except FileEncodingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    return FileContentResponse(**result)


@router.get("/workspaces/{workspace_id}/files", response_model=FileListResponse)
async def list_workspace_files(
    workspace_id: str,
    path: str = Query("", description="Workspace-relative directory path to list."),
    recursive: bool = Query(False, description="If true, list files recursively."),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List files and directories within a workspace directory.

    - Enforces workspace ownership.
    - Validates path remains inside the workspace root.
    - Returns workspace-relative paths only — no absolute filesystem paths.
    - Skips hidden files (dot-prefixed) and system directories.
    - Directories and files sorted alphabetically.
    """
    ws_service = _get_service(session)
    try:
        workspace = await ws_service.get_workspace(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except (WorkspaceNotFoundError, WorkspaceAccessDeniedError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    file_service = WorkspaceFileService(workspace)
    try:
        result = file_service.list_directory(relative_path=path, recursive=recursive)
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileNotFoundInWorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return FileListResponse(
        workspace_id=result["workspace_id"],
        path=result["path"],
        files=[FileEntry(**f) for f in result["files"]],
        directories=[FileEntry(**d) for d in result["directories"]],
    )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific workspace by ID.

    Returns 404 if the workspace doesn't exist or the user doesn't own it.
    Cross-user access is denied with the same 404 to avoid workspace enumeration.
    """
    service = _get_service(session)
    try:
        workspace = await service.get_workspace(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except (WorkspaceNotFoundError, WorkspaceAccessDeniedError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    return WorkspaceResponse.model_validate(workspace)
