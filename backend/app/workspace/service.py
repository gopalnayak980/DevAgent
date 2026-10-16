"""
Workspace Service — Phase 11.

Business logic for workspace management.
Validates workspace paths to ensure they stay within the allowed root directory.
Enforces user ownership for all operations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from app.config import settings
from app.database.models import Workspace
from app.workspace.repository import WorkspaceRepository

logger = logging.getLogger(__name__)


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace is not found."""
    pass


class WorkspaceAccessDeniedError(Exception):
    """Raised when a user tries to access another user's workspace."""
    pass


class InvalidWorkspacePathError(Exception):
    """Raised when a workspace path is outside the allowed root directory."""
    pass


class DuplicateWorkspaceNameError(Exception):
    """Raised when a user tries to create a workspace with a duplicate name."""
    pass


class WorkspaceService:
    """Service for managing user workspaces.

    Architecture:
        Route → WorkspaceService → WorkspaceRepository → Database

    Security:
        - All paths are resolved and validated against WORKSPACE_ROOT_DIR.
        - User ownership is enforced on every read operation.
        - Path traversal attacks (e.g. '../../etc/passwd') are blocked.
    """

    def __init__(self, repository: WorkspaceRepository) -> None:
        self.repository = repository

    def _validate_and_resolve_path(self, root_path: str) -> str:
        """Validate that the workspace path stays within the allowed root.

        The user provides a *relative* path. We resolve it against
        WORKSPACE_ROOT_DIR and verify it doesn't escape via traversal.

        Returns:
            The resolved absolute path as a string.

        Raises:
            InvalidWorkspacePathError: If the path escapes the allowed root.
        """
        workspace_root = Path(settings.WORKSPACE_ROOT_DIR).resolve()
        # Resolve the user-provided path relative to the workspace root
        resolved = (workspace_root / root_path).resolve()

        # Ensure the resolved path is within the workspace root
        try:
            resolved.relative_to(workspace_root)
        except ValueError:
            raise InvalidWorkspacePathError(
                f"Workspace path must be within the allowed workspace root directory. "
                f"Path traversal is not permitted."
            )

        return str(resolved)

    async def create_workspace(
        self,
        user_id: str,
        name: str,
        root_path: str,
    ) -> Workspace:
        """Create a new workspace for the user.

        Args:
            user_id: The owner of the workspace.
            name: Human-readable workspace name.
            root_path: Relative path under the workspace root.

        Returns:
            The created Workspace.

        Raises:
            InvalidWorkspacePathError: If the path is invalid or escapes the root.
            DuplicateWorkspaceNameError: If the user already has a workspace with this name.
        """
        # Validate and resolve the path
        resolved_path = self._validate_and_resolve_path(root_path)

        # Check for duplicate name
        existing = await self.repository.get_by_user_and_name(user_id, name)
        if existing is not None:
            raise DuplicateWorkspaceNameError(
                f"A workspace named '{name}' already exists."
            )

        # Create the workspace directory if it doesn't exist
        os.makedirs(resolved_path, exist_ok=True)

        workspace = Workspace(
            user_id=user_id,
            name=name,
            root_path=resolved_path,
        )
        created = await self.repository.create(workspace)
        logger.info(
            "Created workspace id=%s name=%s user_id=%s",
            created.id, name, user_id,
        )
        return created

    async def get_workspace(self, workspace_id: str, user_id: str) -> Workspace:
        """Retrieve a workspace by ID, enforcing ownership.

        Args:
            workspace_id: The workspace to retrieve.
            user_id: The requesting user (must be the owner).

        Returns:
            The Workspace.

        Raises:
            WorkspaceNotFoundError: If the workspace doesn't exist.
            WorkspaceAccessDeniedError: If the user doesn't own the workspace.
        """
        workspace = await self.repository.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found.")

        if workspace.user_id != user_id:
            raise WorkspaceAccessDeniedError(
                "You do not have access to this workspace."
            )

        return workspace

    async def list_workspaces(self, user_id: str) -> list[Workspace]:
        """List all workspaces owned by the given user.

        Args:
            user_id: The owner whose workspaces to list.

        Returns:
            A list of Workspace objects.
        """
        return await self.repository.list_by_user(user_id)
