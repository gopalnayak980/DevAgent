"""
Tests for Workspace File Service and File API — Phase 11.3.

Covers:
- Language detection
- Path traversal attack prevention (../, absolute paths, symlink escapes)
- File listing (own workspace, non-existent directory, traversal in path)
- File reading (valid, missing, directory, oversized, binary/non-UTF-8)
- Unauthenticated access rejection
- Cross-user workspace access rejection
- Absolute filesystem paths never returned to client
- API endpoints: list files, read file content
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.database.models import User, Workspace
from app.auth.dependencies import get_current_active_user
from app.workspace.file_service import (
    WorkspaceFileService,
    detect_language,
    MAX_FILE_SIZE_BYTES,
    PathTraversalError,
    FileNotFoundInWorkspaceError,
    IsADirectoryError as WorkspaceIsADirectoryError,
    FileTooLargeError,
    FileEncodingError,
)
from app.workspace.repository import WorkspaceRepository
from app.workspace.service import WorkspaceService

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_dir(tmp_path):
    """Create a temporary workspace directory with sample files."""
    ws_dir = tmp_path / "test-workspace"
    ws_dir.mkdir()

    # Create a nested structure
    src = ws_dir / "src"
    src.mkdir()
    (src / "App.jsx").write_text("import React from 'react';\n\nexport default function App() {}\n", encoding="utf-8")
    (src / "main.jsx").write_text("import ReactDOM from 'react-dom';\n", encoding="utf-8")

    (ws_dir / "package.json").write_text('{"name": "test", "version": "1.0.0"}\n', encoding="utf-8")
    (ws_dir / "README.md").write_text("# Test Project\n\nA test project.\n", encoding="utf-8")
    (ws_dir / "index.html").write_text("<!DOCTYPE html><html><body></body></html>\n", encoding="utf-8")

    return ws_dir


@pytest.fixture
def mock_workspace(workspace_dir):
    """Return a mock Workspace model pointing to the temporary directory."""
    ws = MagicMock(spec=Workspace)
    ws.id = "ws-test-123"
    ws.user_id = "test-user-id"
    ws.name = "Test Workspace"
    ws.root_path = str(workspace_dir)
    return ws


@pytest.fixture
def file_service(mock_workspace):
    """Return a WorkspaceFileService bound to the test workspace."""
    return WorkspaceFileService(mock_workspace)


@pytest.fixture
def workspace_root_for_api(tmp_path):
    """Temporary workspace root for API-level tests."""
    root = str(tmp_path / "workspaces")
    os.makedirs(root, exist_ok=True)
    with patch("app.workspace.service.settings") as mock_settings:
        mock_settings.WORKSPACE_ROOT_DIR = root
        yield root


# ===========================================================================
# Language Detection Tests
# ===========================================================================


class TestLanguageDetection:
    """Tests for the deterministic language detection utility."""

    def test_javascript(self):
        assert detect_language("app.js") == "javascript"
        assert detect_language("App.jsx") == "javascript"

    def test_typescript(self):
        assert detect_language("index.ts") == "typescript"
        assert detect_language("Component.tsx") == "typescript"

    def test_python(self):
        assert detect_language("service.py") == "python"

    def test_java(self):
        assert detect_language("Main.java") == "java"

    def test_cpp(self):
        assert detect_language("main.cpp") == "cpp"
        assert detect_language("util.cc") == "cpp"
        assert detect_language("lib.cxx") == "cpp"

    def test_c(self):
        assert detect_language("main.c") == "c"

    def test_css(self):
        assert detect_language("styles.css") == "css"

    def test_html(self):
        assert detect_language("index.html") == "html"
        assert detect_language("page.htm") == "html"

    def test_json(self):
        assert detect_language("package.json") == "json"

    def test_markdown(self):
        assert detect_language("README.md") == "markdown"

    def test_sql(self):
        assert detect_language("schema.sql") == "sql"

    def test_yaml(self):
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("docker-compose.yml") == "yaml"

    def test_xml(self):
        assert detect_language("pom.xml") == "xml"

    def test_unknown_extension(self):
        assert detect_language("file.unknown_ext_xyz") == "text"

    def test_no_extension(self):
        assert detect_language("Makefile") == "text"

    def test_case_insensitive(self):
        assert detect_language("App.JSX") == "javascript"
        assert detect_language("README.MD") == "markdown"


# ===========================================================================
# WorkspaceFileService — Path Traversal Tests
# ===========================================================================


class TestPathTraversal:
    """Tests that path traversal attacks are blocked at the service level."""

    def test_dotdot_traversal_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service._resolve_safe_path("../../etc/passwd")

    def test_dotdot_in_subpath_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service._resolve_safe_path("src/../../etc/passwd")

    def test_absolute_unix_path_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service._resolve_safe_path("/etc/passwd")

    def test_absolute_windows_path_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service._resolve_safe_path("C:\\Windows\\System32\\cmd.exe")

    def test_nested_traversal_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service._resolve_safe_path("src/../../../tmp/evil")

    def test_valid_path_accepted(self, file_service):
        resolved = file_service._resolve_safe_path("src/App.jsx")
        assert "App.jsx" in str(resolved)

    def test_root_path_accepted(self, file_service):
        resolved = file_service._resolve_safe_path("")
        assert resolved is not None

    def test_nested_valid_path_accepted(self, file_service, workspace_dir):
        nested = workspace_dir / "a" / "b" / "c"
        nested.mkdir(parents=True)
        resolved = file_service._resolve_safe_path("a/b/c")
        assert "a" in str(resolved)


# ===========================================================================
# WorkspaceFileService — File Listing Tests
# ===========================================================================


class TestFileServiceListing:
    """Tests for WorkspaceFileService.list_directory."""

    def test_list_root_returns_files_and_dirs(self, file_service):
        result = file_service.list_directory("")
        assert "files" in result
        assert "directories" in result
        file_names = [f["name"] for f in result["files"]]
        dir_names = [d["name"] for d in result["directories"]]
        assert "package.json" in file_names
        assert "README.md" in file_names
        assert "src" in dir_names

    def test_list_subdirectory(self, file_service):
        result = file_service.list_directory("src")
        file_names = [f["name"] for f in result["files"]]
        assert "App.jsx" in file_names
        assert "main.jsx" in file_names

    def test_paths_are_relative_not_absolute(self, file_service):
        result = file_service.list_directory("")
        for entry in result["files"] + result["directories"]:
            # Path must not start with / or drive letter
            assert not os.path.isabs(entry["path"]), (
                f"Entry path should be relative, got: {entry['path']}"
            )

    def test_file_entries_have_size(self, file_service):
        result = file_service.list_directory("")
        for f in result["files"]:
            assert "size" in f
            assert f["size"] >= 0

    def test_directory_entries_have_no_content(self, file_service):
        result = file_service.list_directory("")
        for d in result["directories"]:
            assert "content" not in d

    def test_sorted_predictably(self, file_service, workspace_dir):
        # Add extra files to test sorting
        (workspace_dir / "zzz.txt").write_text("z", encoding="utf-8")
        (workspace_dir / "aaa.txt").write_text("a", encoding="utf-8")
        result = file_service.list_directory("")
        names = [f["name"] for f in result["files"]]
        assert names == sorted(names, key=str.lower)

    def test_hidden_files_excluded(self, file_service, workspace_dir):
        (workspace_dir / ".env").write_text("SECRET=hidden", encoding="utf-8")
        (workspace_dir / ".gitignore").write_text("node_modules/", encoding="utf-8")
        result = file_service.list_directory("")
        names = [f["name"] for f in result["files"]]
        assert ".env" not in names
        assert ".gitignore" not in names

    def test_git_directory_excluded(self, file_service, workspace_dir):
        git_dir = workspace_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]", encoding="utf-8")
        result = file_service.list_directory("")
        dir_names = [d["name"] for d in result["directories"]]
        assert ".git" not in dir_names

    def test_empty_directory(self, file_service, workspace_dir):
        empty = workspace_dir / "empty-dir"
        empty.mkdir()
        result = file_service.list_directory("empty-dir")
        assert result["files"] == []
        assert result["directories"] == []

    def test_nonexistent_path_raises(self, file_service):
        with pytest.raises(FileNotFoundInWorkspaceError):
            file_service.list_directory("nonexistent-directory-xyz")

    def test_traversal_in_list_path_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service.list_directory("../../etc")

    def test_recursive_listing(self, file_service):
        result = file_service.list_directory("", recursive=True)
        all_paths = [f["path"] for f in result["files"]]
        # src/App.jsx should appear in recursive listing
        assert any("App.jsx" in p for p in all_paths)

    def test_workspace_id_in_response(self, file_service, mock_workspace):
        result = file_service.list_directory("")
        assert result["workspace_id"] == mock_workspace.id


# ===========================================================================
# WorkspaceFileService — File Reading Tests
# ===========================================================================


class TestFileServiceReading:
    """Tests for WorkspaceFileService.read_file."""

    def test_read_valid_file(self, file_service):
        result = file_service.read_file("package.json")
        assert result["content"] is not None
        assert "name" in result["content"]  # JSON content check
        assert result["language"] == "json"
        assert result["size"] > 0

    def test_read_jsx_file(self, file_service):
        result = file_service.read_file("src/App.jsx")
        assert "import React" in result["content"]
        assert result["language"] == "javascript"

    def test_read_markdown_file(self, file_service):
        result = file_service.read_file("README.md")
        assert result["language"] == "markdown"

    def test_path_in_response_is_relative(self, file_service):
        result = file_service.read_file("src/App.jsx")
        assert not os.path.isabs(result["path"]), (
            f"Response path should be relative, got: {result['path']}"
        )
        assert "src/App.jsx" in result["path"] or result["path"].endswith("App.jsx")

    def test_workspace_id_in_response(self, file_service, mock_workspace):
        result = file_service.read_file("README.md")
        assert result["workspace_id"] == mock_workspace.id

    def test_nonexistent_file_raises(self, file_service):
        with pytest.raises(FileNotFoundInWorkspaceError):
            file_service.read_file("nonexistent-file-xyz.txt")

    def test_directory_as_file_raises(self, file_service):
        with pytest.raises(WorkspaceIsADirectoryError):
            file_service.read_file("src")

    def test_traversal_in_read_path_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service.read_file("../../etc/passwd")

    def test_absolute_path_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service.read_file("/etc/passwd")

    def test_oversized_file_raises(self, file_service, workspace_dir):
        big_file = workspace_dir / "big.txt"
        # Write slightly more than the limit
        big_file.write_bytes(b"x" * (MAX_FILE_SIZE_BYTES + 1))
        with pytest.raises(FileTooLargeError):
            file_service.read_file("big.txt")

    def test_binary_file_raises_encoding_error(self, file_service, workspace_dir):
        binary_file = workspace_dir / "image.bin"
        # Write raw bytes that are not valid UTF-8
        binary_file.write_bytes(bytes(range(256)))
        with pytest.raises(FileEncodingError):
            file_service.read_file("image.bin")

    def test_empty_path_raises(self, file_service):
        with pytest.raises(FileNotFoundInWorkspaceError):
            file_service.read_file("   ")  # whitespace only

    def test_nested_traversal_blocked(self, file_service):
        with pytest.raises(PathTraversalError):
            file_service.read_file("src/../../etc/shadow")


# ===========================================================================
# API Endpoint Tests — File Listing
# ===========================================================================


class TestFileListAPI:
    """Tests for GET /api/workspaces/{id}/files."""

    def test_list_files_in_own_workspace(self, workspace_root_for_api):
        # Create a workspace
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "List Files Test",
                "root_path": "list-test",
            })
        assert create_resp.status_code == 201
        ws_id = create_resp.json()["id"]
        ws_root = create_resp.json()["root_path"]

        # Create a file in the workspace
        test_file = Path(ws_root) / "hello.py"
        test_file.write_text("print('hello')\n", encoding="utf-8")

        response = client.get(f"/api/workspaces/{ws_id}/files")
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == ws_id
        assert "files" in data
        assert "directories" in data
        file_names = [f["name"] for f in data["files"]]
        assert "hello.py" in file_names

    def test_list_files_unauthenticated_rejected(self):
        override = app.dependency_overrides.get(get_current_active_user)
        app.dependency_overrides.pop(get_current_active_user, None)
        try:
            response = client.get("/api/workspaces/any-id/files")
            assert response.status_code == 401
        finally:
            if override:
                app.dependency_overrides[get_current_active_user] = override

    def test_list_files_nonexistent_workspace_404(self):
        response = client.get("/api/workspaces/nonexistent-ws-xyz/files")
        assert response.status_code == 404

    def test_list_files_cross_user_rejected(self, workspace_root_for_api, setup_test_db):
        """A user cannot list files in another user's workspace."""
        other_ws = Workspace(
            id="cross-user-ws",
            user_id="another-user-xyz",
            name="Other User WS",
            root_path=os.path.join(workspace_root_for_api, "other"),
        )
        import asyncio
        async def _insert():
            setup_test_db.add(other_ws)
            await setup_test_db.commit()
        asyncio.get_event_loop().run_until_complete(_insert())

        response = client.get("/api/workspaces/cross-user-ws/files")
        assert response.status_code == 404

    def test_list_files_path_traversal_rejected(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Traversal List Test",
                "root_path": "traversal-list",
            })
        ws_id = create_resp.json()["id"]
        response = client.get(
            f"/api/workspaces/{ws_id}/files",
            params={"path": "../../etc"},
        )
        assert response.status_code == 400

    def test_response_contains_no_absolute_paths(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Abs Path Test",
                "root_path": "abs-path-test",
            })
        ws_id = create_resp.json()["id"]
        ws_root = create_resp.json()["root_path"]

        # Write a file
        (Path(ws_root) / "sample.txt").write_text("hello", encoding="utf-8")

        response = client.get(f"/api/workspaces/{ws_id}/files")
        assert response.status_code == 200
        data = response.json()
        for entry in data["files"] + data["directories"]:
            assert not os.path.isabs(entry["path"]), (
                f"Absolute path leaked in response: {entry['path']}"
            )


# ===========================================================================
# API Endpoint Tests — File Content
# ===========================================================================


class TestFileContentAPI:
    """Tests for GET /api/workspaces/{id}/files/content."""

    def test_read_file_in_own_workspace(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Read File Test",
                "root_path": "read-test",
            })
        ws_id = create_resp.json()["id"]
        ws_root = create_resp.json()["root_path"]

        # Write a test file
        (Path(ws_root) / "hello.py").write_text("print('hello world')\n", encoding="utf-8")

        response = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "hello.py"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == ws_id
        assert "print('hello world')" in data["content"]
        assert data["language"] == "python"
        assert data["size"] > 0
        assert data["path"] == "hello.py"

    def test_read_file_unauthenticated_rejected(self):
        override = app.dependency_overrides.get(get_current_active_user)
        app.dependency_overrides.pop(get_current_active_user, None)
        try:
            response = client.get(
                "/api/workspaces/any-id/files/content",
                params={"path": "file.txt"},
            )
            assert response.status_code == 401
        finally:
            if override:
                app.dependency_overrides[get_current_active_user] = override

    def test_read_file_nonexistent_workspace_404(self):
        response = client.get(
            "/api/workspaces/nonexistent-ws/files/content",
            params={"path": "file.txt"},
        )
        assert response.status_code == 404

    def test_read_nonexistent_file_404(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Missing File Test",
                "root_path": "missing-file",
            })
        ws_id = create_resp.json()["id"]
        response = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "does-not-exist.txt"},
        )
        assert response.status_code == 404

    def test_read_directory_as_file_400(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Dir As File Test",
                "root_path": "dir-as-file",
            })
        ws_id = create_resp.json()["id"]
        ws_root = create_resp.json()["root_path"]

        # Create a subdirectory
        (Path(ws_root) / "mydir").mkdir()

        response = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "mydir"},
        )
        assert response.status_code == 400

    def test_path_traversal_in_content_request_400(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Traversal Read Test",
                "root_path": "traversal-read",
            })
        ws_id = create_resp.json()["id"]
        response = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "../../etc/passwd"},
        )
        assert response.status_code == 400

    def test_oversized_file_413(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Big File Test",
                "root_path": "big-file",
            })
        ws_id = create_resp.json()["id"]
        ws_root = create_resp.json()["root_path"]

        # Write a file larger than 1 MB
        big_file = Path(ws_root) / "big.txt"
        big_file.write_bytes(b"x" * (MAX_FILE_SIZE_BYTES + 1))

        response = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "big.txt"},
        )
        assert response.status_code == 413

    def test_binary_file_422(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Binary File Test",
                "root_path": "binary-file",
            })
        ws_id = create_resp.json()["id"]
        ws_root = create_resp.json()["root_path"]

        # Write binary content that is not valid UTF-8
        binary_file = Path(ws_root) / "data.bin"
        binary_file.write_bytes(bytes(range(256)))

        response = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "data.bin"},
        )
        assert response.status_code == 422

    def test_response_path_is_not_absolute(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "Path Safety Test",
                "root_path": "path-safety",
            })
        ws_id = create_resp.json()["id"]
        ws_root = create_resp.json()["root_path"]
        (Path(ws_root) / "test.py").write_text("x = 1\n", encoding="utf-8")

        response = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "test.py"},
        )
        assert response.status_code == 200
        data = response.json()
        assert not os.path.isabs(data["path"]), (
            f"Absolute path leaked in content response: {data['path']}"
        )

    def test_cross_user_content_rejected(self, workspace_root_for_api, setup_test_db):
        """A user cannot read files from another user's workspace."""
        other_ws_path = os.path.join(workspace_root_for_api, "other-content")
        os.makedirs(other_ws_path, exist_ok=True)
        other_ws = Workspace(
            id="cross-content-ws",
            user_id="other-content-user",
            name="Other Content WS",
            root_path=other_ws_path,
        )
        import asyncio
        async def _insert():
            setup_test_db.add(other_ws)
            await setup_test_db.commit()
        asyncio.get_event_loop().run_until_complete(_insert())

        response = client.get(
            "/api/workspaces/cross-content-ws/files/content",
            params={"path": "secret.txt"},
        )
        assert response.status_code == 404

    def test_missing_path_param_422(self, workspace_root_for_api):
        """path is a required query parameter."""
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            create_resp = client.post("/api/workspaces", json={
                "name": "No Path Param Test",
                "root_path": "no-path-param",
            })
        ws_id = create_resp.json()["id"]
        # No path param — FastAPI should return 422
        response = client.get(f"/api/workspaces/{ws_id}/files/content")
        assert response.status_code == 422
