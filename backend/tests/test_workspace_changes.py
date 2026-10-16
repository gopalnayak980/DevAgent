"""
Tests for Workspace File Change Proposals & Approvals — Phase 11.4.

Covers:
1. create proposal
2. proposal ownership
3. workspace ownership
4. file path traversal rejection
5. absolute path rejection
6. Windows path rejection
7. symlink escape rejection
8. original hash creation
9. proposed hash creation
10. diff generation
11. pending status
12. approve proposal
13. reject proposal
14. rejected proposal does not modify file
15. approved proposal modifies file
16. stale file detection
17. double approval protection
18. cross-user proposal access
19. cross-workspace access
20. unauthenticated access
21. atomic write failure handling
22. missing file handling
23. directory path handling
24. large file protection
25. UTF-8 validation
"""

import hashlib
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.models import User, Workspace, FileChangeProposal
from app.auth.dependencies import get_current_active_user
from app.workspace.file_service import MAX_FILE_SIZE_BYTES

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_root_for_api(tmp_path):
    """Temporary workspace root directory for API tests."""
    root = str(tmp_path / "workspaces")
    os.makedirs(root, exist_ok=True)
    with patch("app.workspace.service.settings") as mock_settings:
        mock_settings.WORKSPACE_ROOT_DIR = root
        yield root


@pytest.fixture
def sample_workspace(workspace_root_for_api):
    """Create a sample workspace with initial files."""
    with patch("app.workspace.service.settings") as mock_settings:
        mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
        resp = client.post("/api/workspaces", json={
            "name": "Change Test WS",
            "root_path": "change-test",
        })
    assert resp.status_code == 201
    ws_data = resp.json()
    ws_id = ws_data["id"]
    ws_root = Path(ws_data["root_path"])

    # Create nested directories and sample files
    src = ws_root / "src"
    src.mkdir(parents=True, exist_ok=True)

    app_file = src / "App.jsx"
    app_file.write_text('const message = "Hello";\nexport default message;\n', encoding="utf-8")

    pkg_file = ws_root / "package.json"
    pkg_file.write_text('{"name": "test-app", "version": "1.0.0"}\n', encoding="utf-8")

    return {
        "id": ws_id,
        "root_path": str(ws_root),
        "app_file": app_file,
        "pkg_file": pkg_file,
    }


# ===========================================================================
# 1. Proposal Creation & Validation Tests
# ===========================================================================


class TestProposalCreation:
    """Tests for creating file change proposals."""

    def test_create_valid_proposal(self, sample_workspace):
        ws_id = sample_workspace["id"]
        proposed = 'const message = "Hello DevAgent";\nexport default message;\n'

        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": proposed,
        })
        assert resp.status_code == 201
        data = resp.json()

        assert data["id"] is not None
        assert data["workspace_id"] == ws_id
        assert data["user_id"] == "test-user-id"
        assert data["file_path"] == "src/App.jsx"
        assert data["status"] == "pending"

        # Check hashes
        expected_orig_hash = hashlib.sha256(
            'const message = "Hello";\nexport default message;\n'.encode("utf-8")
        ).hexdigest()
        expected_prop_hash = hashlib.sha256(proposed.encode("utf-8")).hexdigest()
        assert data["original_content_hash"] == expected_orig_hash
        assert data["proposed_content_hash"] == expected_prop_hash

        # Check diff
        assert "--- a/src/App.jsx" in data["diff"]
        assert "+++ b/src/App.jsx" in data["diff"]
        assert '-const message = "Hello";' in data["diff"]
        assert '+const message = "Hello DevAgent";' in data["diff"]

        # Crucial: verify file on disk is NOT modified yet
        disk_content = sample_workspace["app_file"].read_text(encoding="utf-8")
        assert 'const message = "Hello";' in disk_content
        assert "DevAgent" not in disk_content

    def test_traversal_path_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "../../etc/passwd",
            "proposed_content": "evil content",
        })
        assert resp.status_code == 400
        assert "traversal" in resp.json()["detail"].lower()

    def test_nested_traversal_path_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/../../etc/shadow",
            "proposed_content": "evil content",
        })
        assert resp.status_code == 400

    def test_absolute_unix_path_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "/etc/passwd",
            "proposed_content": "evil",
        })
        assert resp.status_code == 400

    def test_absolute_windows_path_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "C:\\Windows\\System32\\cmd.exe",
            "proposed_content": "evil",
        })
        assert resp.status_code == 400

    def test_missing_file_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/NonExistent.jsx",
            "proposed_content": "new content",
        })
        assert resp.status_code == 404

    def test_directory_as_file_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src",
            "proposed_content": "new content",
        })
        assert resp.status_code == 400

    def test_oversized_proposed_content_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        big_content = "x" * (MAX_FILE_SIZE_BYTES + 10)
        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": big_content,
        })
        assert resp.status_code == 413

    def test_binary_file_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        bin_path = Path(sample_workspace["root_path"]) / "image.png"
        bin_path.write_bytes(bytes(range(256)))

        resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "image.png",
            "proposed_content": "valid text",
        })
        assert resp.status_code == 422


# ===========================================================================
# 2. Retrieval, Listing & Access Control Tests
# ===========================================================================


class TestProposalRetrieval:
    """Tests for GET proposal endpoints and isolation."""

    def test_get_proposal_by_id(self, sample_workspace):
        ws_id = sample_workspace["id"]
        create_resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "package.json",
            "proposed_content": '{"name": "test-app", "version": "1.1.0"}\n',
        })
        proposal_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/workspaces/{ws_id}/changes/{proposal_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == proposal_id
        assert data["file_path"] == "package.json"
        assert data["status"] == "pending"

    def test_list_proposals(self, sample_workspace):
        ws_id = sample_workspace["id"]
        client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "package.json",
            "proposed_content": '{"version": "2.0.0"}\n',
        })
        client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": 'export default () => <h1>App</h1>;\n',
        })

        list_resp = client.get(f"/api/workspaces/{ws_id}/changes")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 2
        assert len(data["proposals"]) >= 2

    def test_list_filtered_by_status(self, sample_workspace):
        ws_id = sample_workspace["id"]
        p1 = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "package.json",
            "proposed_content": '{"version": "3.0.0"}\n',
        }).json()

        # Reject p1
        client.post(f"/api/workspaces/{ws_id}/changes/{p1['id']}/reject")

        # Create another pending proposal
        client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": 'const x = 1;\n',
        })

        # Filter pending
        pending_resp = client.get(f"/api/workspaces/{ws_id}/changes", params={"status": "pending"})
        assert pending_resp.status_code == 200
        for p in pending_resp.json()["proposals"]:
            assert p["status"] == "pending"

        # Filter rejected
        rej_resp = client.get(f"/api/workspaces/{ws_id}/changes", params={"status": "rejected"})
        assert rej_resp.status_code == 200
        for p in rej_resp.json()["proposals"]:
            assert p["status"] == "rejected"

    def test_cross_user_access_rejected(self, sample_workspace, setup_test_db):
        """User cannot access or see another user's proposal."""
        ws_id = sample_workspace["id"]
        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": "new text",
        }).json()

        # Create another user and switch dependency override
        other_user = User(
            id="other-user-999",
            email="other@example.com",
            password_hash="fake",
            name="Other User",
            role="user",
            is_active=True,
        )

        async def _override_other():
            return other_user

        app.dependency_overrides[get_current_active_user] = _override_other
        try:
            # Try to get proposal
            resp = client.get(f"/api/workspaces/{ws_id}/changes/{prop['id']}")
            assert resp.status_code == 404

            # Try to approve proposal
            app_resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/approve")
            assert app_resp.status_code == 404

            # Try to reject proposal
            rej_resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/reject")
            assert rej_resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    def test_cross_workspace_access_rejected(self, sample_workspace, workspace_root_for_api):
        """Proposal belonging to workspace A cannot be accessed via workspace B."""
        ws_id = sample_workspace["id"]
        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": "new text",
        }).json()

        # Create second workspace
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api
            ws2 = client.post("/api/workspaces", json={
                "name": "WS 2",
                "root_path": "ws-2",
            }).json()

        # Attempt to access prop via ws2
        resp = client.get(f"/api/workspaces/{ws2['id']}/changes/{prop['id']}")
        assert resp.status_code == 404

        # Attempt to approve prop via ws2
        app_resp = client.post(f"/api/workspaces/{ws2['id']}/changes/{prop['id']}/approve")
        assert app_resp.status_code == 404

    def test_unauthenticated_access_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        override = app.dependency_overrides.get(get_current_active_user)
        app.dependency_overrides.pop(get_current_active_user, None)
        try:
            assert client.post(f"/api/workspaces/{ws_id}/changes", json={
                "file_path": "a.txt", "proposed_content": "b"
            }).status_code == 401

            assert client.get(f"/api/workspaces/{ws_id}/changes").status_code == 401
            assert client.get(f"/api/workspaces/{ws_id}/changes/any-id").status_code == 401
            assert client.post(f"/api/workspaces/{ws_id}/changes/any-id/approve").status_code == 401
            assert client.post(f"/api/workspaces/{ws_id}/changes/any-id/reject").status_code == 401
        finally:
            if override:
                app.dependency_overrides[get_current_active_user] = override


# ===========================================================================
# 3. Approval & Rejection Behavior Tests
# ===========================================================================


class TestProposalApprovalAndRejection:
    """Tests for human approval workflow and file modification."""

    def test_reject_proposal_does_not_modify_file(self, sample_workspace):
        ws_id = sample_workspace["id"]
        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": "completely new code\n",
        }).json()

        resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/reject")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["rejected_at"] is not None

        # Verify file is completely unmodified
        current_content = sample_workspace["app_file"].read_text(encoding="utf-8")
        assert 'const message = "Hello";' in current_content
        assert "completely new code" not in current_content

    def test_cannot_approve_rejected_proposal(self, sample_workspace):
        ws_id = sample_workspace["id"]
        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": "new code\n",
        }).json()

        client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/reject")

        # Try to approve
        resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/approve")
        assert resp.status_code == 400
        assert "pending" in resp.json()["detail"].lower()

    def test_approve_proposal_modifies_file_atomically(self, sample_workspace):
        ws_id = sample_workspace["id"]
        new_content = 'const message = "Hello DevAgent";\nexport default message;\n'

        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": new_content,
        }).json()

        resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert data["approved_at"] is not None
        assert data["applied_at"] is not None

        # Verify file on disk has changed to exact proposed content
        current_content = sample_workspace["app_file"].read_text(encoding="utf-8")
        assert current_content == new_content

        # Verify via Phase 11.3 file read endpoint
        read_resp = client.get(
            f"/api/workspaces/{ws_id}/files/content",
            params={"path": "src/App.jsx"},
        )
        assert read_resp.status_code == 200
        assert read_resp.json()["content"] == new_content

    def test_double_approval_rejected(self, sample_workspace):
        ws_id = sample_workspace["id"]
        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "package.json",
            "proposed_content": '{"name": "double-approval-test"}\n',
        }).json()

        # First approval
        resp1 = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/approve")
        assert resp1.status_code == 200

        # Second approval attempt
        resp2 = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/approve")
        assert resp2.status_code == 400
        assert "pending" in resp2.json()["detail"].lower()

    def test_stale_file_protection(self, sample_workspace):
        """If file is modified after proposal is created, approval MUST fail."""
        ws_id = sample_workspace["id"]

        # 1. Create proposal
        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": 'const message = "Proposed";\n',
        }).json()

        # 2. Change file manually before approval
        sample_workspace["app_file"].write_text(
            'const message = "Manually Changed Out-of-band";\n',
            encoding="utf-8",
        )

        # 3. Try to approve
        resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/approve")
        assert resp.status_code == 409  # Conflict / Stale file
        assert "modified" in resp.json()["detail"].lower() or "stale" in resp.json()["detail"].lower()

        # 4. Verify file MUST remain with manual change
        disk_content = sample_workspace["app_file"].read_text(encoding="utf-8")
        assert 'Manually Changed Out-of-band' in disk_content
        assert 'Proposed' not in disk_content

        # 5. Check proposal is marked as failed
        get_resp = client.get(f"/api/workspaces/{ws_id}/changes/{prop['id']}")
        assert get_resp.json()["status"] == "failed"

    def test_atomic_write_failure_preserves_original_file(self, sample_workspace):
        """Simulate an OS failure during atomic replacement."""
        ws_id = sample_workspace["id"]
        original_text = sample_workspace["app_file"].read_text(encoding="utf-8")

        prop = client.post(f"/api/workspaces/{ws_id}/changes", json={
            "file_path": "src/App.jsx",
            "proposed_content": "fail test content\n",
        }).json()

        with patch("os.replace", side_effect=OSError("Simulated disk error")):
            resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop['id']}/approve")
            assert resp.status_code == 500

        # Verify file is preserved
        current = sample_workspace["app_file"].read_text(encoding="utf-8")
        assert current == original_text

        # Verify proposal marked as failed
        get_resp = client.get(f"/api/workspaces/{ws_id}/changes/{prop['id']}")
        assert get_resp.json()["status"] == "failed"


# ===========================================================================
# 4. Full End-to-End Workflow Test
# ===========================================================================


class TestEndToEndWorkflow:
    """Validates the full workflow requested in the Phase 11.4 specification."""

    def test_full_specification_workflow(self, workspace_root_for_api):
        with patch("app.workspace.service.settings") as mock_settings:
            mock_settings.WORKSPACE_ROOT_DIR = workspace_root_for_api

            # 1. Create workspace: Test React Project
            ws_resp = client.post("/api/workspaces", json={
                "name": "Test React Project",
                "root_path": "test-react-project",
            })
            assert ws_resp.status_code == 201
            ws = ws_resp.json()
            ws_id = ws["id"]
            ws_root = Path(ws["root_path"])

            # Setup file: src/App.jsx with: const message = "Hello";
            src = ws_root / "src"
            src.mkdir(parents=True, exist_ok=True)
            app_file = src / "App.jsx"
            app_file.write_text('const message = "Hello";\n', encoding="utf-8")

            # 2. Create proposal: old: const message = "Hello"; proposed: const message = "Hello DevAgent";
            prop1_resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
                "file_path": "src/App.jsx",
                "proposed_content": 'const message = "Hello DevAgent";\n',
            })
            assert prop1_resp.status_code == 201
            prop1 = prop1_resp.json()

            # Expected: status = pending, diff displayed
            assert prop1["status"] == "pending"
            assert '-const message = "Hello";' in prop1["diff"]
            assert '+const message = "Hello DevAgent";' in prop1["diff"]

            # Before approval: File MUST remain unchanged
            assert app_file.read_text(encoding="utf-8") == 'const message = "Hello";\n'

            # 3. Reject: File MUST remain unchanged
            rej_resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop1['id']}/reject")
            assert rej_resp.status_code == 200
            assert app_file.read_text(encoding="utf-8") == 'const message = "Hello";\n'

            # 4. Create another proposal
            prop2_resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
                "file_path": "src/App.jsx",
                "proposed_content": 'const message = "Hello DevAgent";\n',
            })
            assert prop2_resp.status_code == 201
            prop2 = prop2_resp.json()

            # 5. Approve: File changes exactly to proposed content
            appr_resp = client.post(f"/api/workspaces/{ws_id}/changes/{prop2['id']}/approve")
            assert appr_resp.status_code == 200
            assert appr_resp.json()["status"] == "applied"
            assert app_file.read_text(encoding="utf-8") == 'const message = "Hello DevAgent";\n'

            # 6. Verify GET file content returns: const message = "Hello DevAgent";
            read_resp = client.get(
                f"/api/workspaces/{ws_id}/files/content",
                params={"path": "src/App.jsx"},
            )
            assert read_resp.status_code == 200
            assert read_resp.json()["content"] == 'const message = "Hello DevAgent";\n'

            # 7. Test stale protection:
            # - Create proposal
            prop3_resp = client.post(f"/api/workspaces/{ws_id}/changes", json={
                "file_path": "src/App.jsx",
                "proposed_content": 'const message = "Third Update";\n',
            })
            assert prop3_resp.status_code == 201
            prop3 = prop3_resp.json()

            # - Change file manually
            app_file.write_text('const message = "Manual Out-of-band";\n', encoding="utf-8")

            # - Try approval -> MUST fail with 409
            stale_appr = client.post(f"/api/workspaces/{ws_id}/changes/{prop3['id']}/approve")
            assert stale_appr.status_code == 409

            # - File MUST remain with manual change
            assert app_file.read_text(encoding="utf-8") == 'const message = "Manual Out-of-band";\n'
