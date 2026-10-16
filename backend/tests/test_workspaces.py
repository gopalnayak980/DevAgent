"""
Tests for Workspace API and Service — Phase 11.

Covers:
- Workspace creation (valid + invalid paths)
- Workspace listing (user isolation)
- Workspace retrieval (ownership enforcement)
- Cross-user access rejection
- Unauthenticated access rejection
- Duplicate name rejection
- Path traversal attack prevention
"""

import pytest
import os
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.models import User, Workspace
from app.auth.dependencies import get_current_active_user
from app.workspace.repository import WorkspaceRepository
from app.workspace.service import (
    WorkspaceService,
    WorkspaceNotFoundError,
    WorkspaceAccessDeniedError,
    InvalidWorkspacePathError,
    DuplicateWorkspaceNameError,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper: create a temporary workspace root for test isolation
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace_root(tmp_path):
    """Provide a temporary workspace root directory and patch config."""
    root = str(tmp_path / "workspaces")
    os.makedirs(root, exist_ok=True)
    with patch("app.workspace.service.settings") as mock_settings:
        mock_settings.WORKSPACE_ROOT_DIR = root
        yield root


# ===========================================================================
# API Endpoint Tests
# ===========================================================================


class TestWorkspaceAPI:
    """Tests for workspace REST endpoints."""

    def test_create_workspace(self, workspace_root):
        """Test creating a workspace via API."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            response = client.post("/api/workspaces", json={
                "name": "My Project",
                "root_path": "my-project",
            })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Project"
        assert "id" in data
        assert "user_id" in data
        assert "root_path" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_list_workspaces(self, workspace_root):
        """Test listing workspaces returns only current user's workspaces."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            # Create two workspaces
            client.post("/api/workspaces", json={
                "name": "Project Alpha",
                "root_path": "alpha",
            })
            client.post("/api/workspaces", json={
                "name": "Project Beta",
                "root_path": "beta",
            })
            response = client.get("/api/workspaces")
        assert response.status_code == 200
        data = response.json()
        assert "workspaces" in data
        assert "total" in data
        assert data["total"] >= 2
        names = [w["name"] for w in data["workspaces"]]
        assert "Project Alpha" in names
        assert "Project Beta" in names

    def test_get_workspace_by_id(self, workspace_root):
        """Test retrieving a workspace by ID."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            create_resp = client.post("/api/workspaces", json={
                "name": "Retrieval Test",
                "root_path": "retrieval-test",
            })
            ws_id = create_resp.json()["id"]

            response = client.get(f"/api/workspaces/{ws_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ws_id
        assert data["name"] == "Retrieval Test"

    def test_get_nonexistent_workspace_returns_404(self):
        """Test that requesting a non-existent workspace returns 404."""
        response = client.get("/api/workspaces/nonexistent-id-12345")
        assert response.status_code == 404

    def test_duplicate_workspace_name_returns_409(self, workspace_root):
        """Test that creating a workspace with a duplicate name returns 409."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            client.post("/api/workspaces", json={
                "name": "Unique Project",
                "root_path": "unique-1",
            })
            response = client.post("/api/workspaces", json={
                "name": "Unique Project",
                "root_path": "unique-2",
            })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_invalid_path_traversal_rejected(self, workspace_root):
        """Test that path traversal attacks are rejected."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            response = client.post("/api/workspaces", json={
                "name": "Evil Project",
                "root_path": "../../etc/passwd",
            })
        assert response.status_code == 400
        assert "traversal" in response.json()["detail"].lower()

    def test_empty_name_rejected(self):
        """Test that an empty workspace name is rejected by validation."""
        response = client.post("/api/workspaces", json={
            "name": "",
            "root_path": "some-path",
        })
        assert response.status_code == 422

    def test_empty_path_rejected(self):
        """Test that an empty root_path is rejected by validation."""
        response = client.post("/api/workspaces", json={
            "name": "Some Project",
            "root_path": "",
        })
        assert response.status_code == 422

    def test_unauthenticated_create_rejected(self):
        """Test that creating a workspace without auth is rejected."""
        override = app.dependency_overrides.get(get_current_active_user)
        app.dependency_overrides.pop(get_current_active_user, None)
        try:
            response = client.post("/api/workspaces", json={
                "name": "Sneaky",
                "root_path": "sneaky",
            })
            assert response.status_code == 401
        finally:
            if override:
                app.dependency_overrides[get_current_active_user] = override

    def test_unauthenticated_list_rejected(self):
        """Test that listing workspaces without auth is rejected."""
        override = app.dependency_overrides.get(get_current_active_user)
        app.dependency_overrides.pop(get_current_active_user, None)
        try:
            response = client.get("/api/workspaces")
            assert response.status_code == 401
        finally:
            if override:
                app.dependency_overrides[get_current_active_user] = override

    def test_unauthenticated_get_rejected(self):
        """Test that getting a workspace without auth is rejected."""
        override = app.dependency_overrides.get(get_current_active_user)
        app.dependency_overrides.pop(get_current_active_user, None)
        try:
            response = client.get("/api/workspaces/some-id")
            assert response.status_code == 401
        finally:
            if override:
                app.dependency_overrides[get_current_active_user] = override


# ===========================================================================
# Cross-User Access Tests
# ===========================================================================


class TestWorkspaceCrossUserAccess:
    """Tests for user ownership enforcement."""

    @pytest.mark.asyncio
    async def test_cross_user_workspace_access_rejected(self, setup_test_db, workspace_root):
        """Test that a user cannot access another user's workspace."""
        session = setup_test_db

        # Create another user
        other_user = User(
            id="other-user-id",
            email="other@example.com",
            password_hash="fake_hash",
            name="Other User",
            role="user",
            is_active=True,
        )
        session.add(other_user)
        await session.commit()

        # Create a workspace directly in the DB for the other user
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(session)
            service = WorkspaceService(repo)
            other_ws = await service.create_workspace(
                user_id="other-user-id",
                name="Other's Project",
                root_path="other-project",
            )

        # Try to access it as the test user (test-user-id from conftest)
        response = client.get(f"/api/workspaces/{other_ws.id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_listing_excludes_other_users_workspaces(self, setup_test_db, workspace_root):
        """Test that listing workspaces only returns the current user's workspaces."""
        session = setup_test_db

        # Create workspaces for different users directly in DB
        ws_mine = Workspace(
            id="ws-mine",
            user_id="test-user-id",
            name="My Workspace",
            root_path=os.path.join(workspace_root, "mine"),
        )
        ws_other = Workspace(
            id="ws-other",
            user_id="other-user-id-2",
            name="Their Workspace",
            root_path=os.path.join(workspace_root, "theirs"),
        )
        session.add_all([ws_mine, ws_other])
        await session.commit()

        response = client.get("/api/workspaces")
        assert response.status_code == 200
        data = response.json()
        ws_ids = [w["id"] for w in data["workspaces"]]
        assert "ws-mine" in ws_ids
        assert "ws-other" not in ws_ids


# ===========================================================================
# Service Layer Tests
# ===========================================================================


@pytest.mark.asyncio
class TestWorkspaceService:
    """Tests for workspace business logic."""

    async def test_validate_path_within_root(self, setup_test_db, workspace_root):
        """Test that valid paths within the root are accepted."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            resolved = service._validate_and_resolve_path("my-project")
            assert workspace_root in resolved

    async def test_validate_path_traversal_rejected(self, setup_test_db, workspace_root):
        """Test that path traversal is rejected."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            with pytest.raises(InvalidWorkspacePathError):
                service._validate_and_resolve_path("../../etc/passwd")

    async def test_validate_absolute_path_outside_root_rejected(self, setup_test_db, workspace_root):
        """Test that absolute paths outside the root are rejected."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            # On Windows, an absolute path to a different drive or location
            # After resolution, it should still be caught
            with pytest.raises(InvalidWorkspacePathError):
                service._validate_and_resolve_path("../../../tmp/evil")

    async def test_create_workspace_creates_directory(self, setup_test_db, workspace_root):
        """Test that creating a workspace also creates the directory on disk."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            ws = await service.create_workspace(
                user_id="test-user-id",
                name="Dir Test Project",
                root_path="dir-test",
            )
            assert os.path.isdir(ws.root_path)

    async def test_create_duplicate_name_raises(self, setup_test_db, workspace_root):
        """Test that duplicate workspace names for the same user raise an error."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            await service.create_workspace(
                user_id="test-user-id",
                name="Duplicate Name",
                root_path="dup-1",
            )
            with pytest.raises(DuplicateWorkspaceNameError):
                await service.create_workspace(
                    user_id="test-user-id",
                    name="Duplicate Name",
                    root_path="dup-2",
                )

    async def test_get_workspace_enforces_ownership(self, setup_test_db, workspace_root):
        """Test that get_workspace raises when user doesn't own the workspace."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            ws = await service.create_workspace(
                user_id="test-user-id",
                name="Owned Project",
                root_path="owned-proj",
            )
            with pytest.raises(WorkspaceAccessDeniedError):
                await service.get_workspace(ws.id, user_id="attacker-user-id")

    async def test_get_nonexistent_workspace_raises(self, setup_test_db, workspace_root):
        """Test that getting a non-existent workspace raises WorkspaceNotFoundError."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            with pytest.raises(WorkspaceNotFoundError):
                await service.get_workspace("nonexistent-id", user_id="test-user-id")

    async def test_list_workspaces_returns_only_user_workspaces(self, setup_test_db, workspace_root):
        """Test that list_workspaces only returns workspaces for the specified user."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)

            await service.create_workspace("test-user-id", "Project A", "proj-a")
            await service.create_workspace("test-user-id", "Project B", "proj-b")

            # Create a workspace for another user directly in the repo
            other_ws = Workspace(
                user_id="another-user-id",
                name="Other Project",
                root_path=os.path.join(workspace_root, "other-proj"),
            )
            await repo.create(other_ws)

            user_workspaces = await service.list_workspaces("test-user-id")
            assert len(user_workspaces) == 2
            assert all(w.user_id == "test-user-id" for w in user_workspaces)

    async def test_nested_path_within_root_accepted(self, setup_test_db, workspace_root):
        """Test that nested subdirectory paths within the root are accepted."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root
            repo = WorkspaceRepository(setup_test_db)
            service = WorkspaceService(repo)
            ws = await service.create_workspace(
                user_id="test-user-id",
                name="Nested Project",
                root_path="org/team/nested-project",
            )
            assert os.path.isdir(ws.root_path)
            assert workspace_root in ws.root_path
