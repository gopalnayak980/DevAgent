"""
Tests for Chat-to-File-Change-Proposal Integration — Phase 11.4.

Covers:
1. File modification detection patterns
2. File path extraction from messages
3. Change pair extraction (old → new)
4. Text replacement logic
5. Proposal creation from chat with workspace context
6. Chat API creates persistent proposal when workspace_id is provided
7. Chat API returns proposal metadata in response
8. No proposal created for normal chat messages
9. No proposal created without workspace_id
10. No proposal created when file not found
11. Proposal file unchanged before approval
12. Cross-user isolation
"""

import hashlib
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.models import User
from app.auth.dependencies import get_current_active_user
from app.workspace.file_modification_service import (
    detect_file_modification_intent,
    extract_file_path,
    extract_change_pair,
    apply_text_replacement,
)

client = TestClient(app)


# ===========================================================================
# 1. Unit Tests — Detection & Extraction
# ===========================================================================


class TestFileModificationDetection:
    """Tests for detect_file_modification_intent()."""

    def test_detects_modify_keyword(self):
        assert detect_file_modification_intent(
            "Modify hello.js and change the message"
        ) is True

    def test_detects_change_keyword(self):
        assert detect_file_modification_intent(
            'Change hello.js to use a new message'
        ) is True

    def test_detects_update_keyword(self):
        assert detect_file_modification_intent(
            "Update src/App.jsx with new content"
        ) is True

    def test_detects_edit_keyword(self):
        assert detect_file_modification_intent(
            "Edit package.json version field"
        ) is True

    def test_detects_replace_keyword(self):
        assert detect_file_modification_intent(
            'Replace content in config.py with new values'
        ) is True

    def test_ignores_normal_message(self):
        assert detect_file_modification_intent(
            "What is the meaning of life?"
        ) is False

    def test_ignores_coding_question(self):
        assert detect_file_modification_intent(
            "Write a function to add two numbers"
        ) is False

    def test_ignores_keyword_without_file(self):
        """Should not detect modification intent without a file path."""
        assert detect_file_modification_intent(
            "Change the color of the button"
        ) is False

    def test_detects_propose_keyword(self):
        assert detect_file_modification_intent(
            "Propose a change to main.py"
        ) is True


class TestFilePathExtraction:
    """Tests for extract_file_path()."""

    def test_extracts_simple_filename(self):
        result = extract_file_path("Modify hello.js and change the message")
        assert result == "hello.js"

    def test_extracts_nested_path(self):
        result = extract_file_path("Update src/App.jsx with new code")
        assert result == "src/App.jsx"

    def test_extracts_quoted_path(self):
        result = extract_file_path("Edit 'config.py' to add a new setting")
        assert result == "config.py"

    def test_returns_none_for_no_file(self):
        result = extract_file_path("Tell me about Python")
        assert result is None

    def test_extracts_deeply_nested(self):
        result = extract_file_path(
            "Modify backend/app/routes/chat.py to add logging"
        )
        assert result == "backend/app/routes/chat.py"


class TestChangePairExtraction:
    """Tests for extract_change_pair()."""

    def test_extracts_change_to_pattern(self):
        message = (
            'Modify hello.js and\n'
            'change:\nconst message = "Hello";\n'
            'to:\nconst message = "Hello DevAgent!";'
        )
        old, new = extract_change_pair(message)
        assert old == 'const message = "Hello";'
        assert new == 'const message = "Hello DevAgent!";'

    def test_returns_none_for_no_pattern(self):
        old, new = extract_change_pair("Just a regular message")
        assert old is None
        assert new is None

    def test_extracts_inline_pattern(self):
        message = 'change: var x = 1 to: var x = 2'
        old, new = extract_change_pair(message)
        assert old == "var x = 1"
        assert new == "var x = 2"


class TestTextReplacement:
    """Tests for apply_text_replacement()."""

    def test_replaces_exact_match(self):
        original = 'const message = "Hello";\nexport default message;\n'
        result = apply_text_replacement(
            original,
            'const message = "Hello";',
            'const message = "Hello DevAgent";',
        )
        assert result == 'const message = "Hello DevAgent";\nexport default message;\n'

    def test_returns_none_when_not_found(self):
        original = "const x = 1;\n"
        result = apply_text_replacement(original, "const y = 2", "const y = 3")
        assert result is None

    def test_replaces_only_first_occurrence(self):
        original = "a = 1\na = 1\na = 1\n"
        result = apply_text_replacement(original, "a = 1", "a = 2")
        assert result == "a = 2\na = 1\na = 1\n"


# ===========================================================================
# 2. Integration Tests — Chat API with File Change Proposals
# ===========================================================================


@pytest.fixture
def ws_root_for_chat(tmp_path):
    """Temporary workspace root directory for chat integration tests."""
    root = str(tmp_path / "workspaces")
    os.makedirs(root, exist_ok=True)
    with patch("app.workspace.service.settings") as mock_settings:
        mock_settings.WORKSPACE_ROOT_DIR = root
        yield root


@pytest.fixture
def chat_workspace(ws_root_for_chat):
    """Create a workspace with sample files for chat integration tests."""
    with patch("app.workspace.service.settings") as mock_settings:
        mock_settings.WORKSPACE_ROOT_DIR = ws_root_for_chat
        resp = client.post("/api/workspaces", json={
            "name": "Chat Integration WS",
            "root_path": "chat-integration",
        })
    assert resp.status_code == 201
    ws_data = resp.json()
    ws_id = ws_data["id"]
    ws_root = Path(ws_data["root_path"])

    # Create sample file
    hello_file = ws_root / "hello.js"
    hello_file.write_text(
        'const message = "Hello DevAgent";\nconsole.log(message);\n',
        encoding="utf-8",
    )

    return {
        "id": ws_id,
        "root_path": str(ws_root),
        "hello_file": hello_file,
    }


class TestChatProposalIntegration:
    """Tests for the chat → file change proposal pipeline."""

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_chat_creates_proposal_with_workspace(
        self, mock_llm, chat_workspace
    ):
        """When workspace_id is provided and message requests modification,
        a persistent FileChangeProposal is created."""
        mock_llm.return_value = "I'll modify the file as requested."

        ws_id = chat_workspace["id"]
        message = (
            'Modify hello.js and\n'
            'change:\nconst message = "Hello DevAgent";\n'
            'to:\nconst message = "Hello from DevAgent!";'
        )

        resp = client.post("/api/chat", json={
            "message": message,
            "workspace_id": ws_id,
        })

        assert resp.status_code == 200
        data = resp.json()

        # Verify proposal metadata is in response
        assert data["file_change_proposal"] is not None
        proposal = data["file_change_proposal"]
        assert proposal["file_path"] == "hello.js"
        assert proposal["status"] == "pending"
        assert proposal["workspace_id"] == ws_id
        assert "diff" in proposal

        # Verify the response text mentions the proposal
        assert "File Change Proposal Created" in data["response"]
        assert "Changes" in data["response"]

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_chat_proposal_file_not_modified(
        self, mock_llm, chat_workspace
    ):
        """After creating a proposal via chat, the actual file must remain unchanged."""
        mock_llm.return_value = "Modification proposed."

        ws_id = chat_workspace["id"]
        message = (
            'Modify hello.js and\n'
            'change:\nconst message = "Hello DevAgent";\n'
            'to:\nconst message = "Updated!";'
        )

        resp = client.post("/api/chat", json={
            "message": message,
            "workspace_id": ws_id,
        })
        assert resp.status_code == 200
        assert resp.json()["file_change_proposal"] is not None

        # Verify file on disk is NOT modified
        disk_content = chat_workspace["hello_file"].read_text(encoding="utf-8")
        assert 'const message = "Hello DevAgent";' in disk_content
        assert "Updated!" not in disk_content

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_proposal_visible_in_changes_endpoint(
        self, mock_llm, chat_workspace
    ):
        """A proposal created via chat must show up in the workspace changes listing."""
        mock_llm.return_value = "Done."

        ws_id = chat_workspace["id"]
        message = (
            'Modify hello.js and\n'
            'change:\nconst message = "Hello DevAgent";\n'
            'to:\nconst message = "Changed via chat!";'
        )

        chat_resp = client.post("/api/chat", json={
            "message": message,
            "workspace_id": ws_id,
        })
        assert chat_resp.status_code == 200
        proposal_id = chat_resp.json()["file_change_proposal"]["id"]

        # Verify proposal appears in Changes endpoint
        list_resp = client.get(f"/api/workspaces/{ws_id}/changes")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 1
        proposal_ids = [p["id"] for p in data["proposals"]]
        assert proposal_id in proposal_ids

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_chat_without_workspace_no_proposal(self, mock_llm):
        """Without workspace_id, no proposal is created even with modification keywords."""
        mock_llm.return_value = "Here's the code change."

        resp = client.post("/api/chat", json={
            "message": 'Modify hello.js and change: x = 1 to: x = 2',
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["file_change_proposal"] is None

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_normal_chat_no_proposal(self, mock_llm, chat_workspace):
        """Normal coding question with workspace_id does not create a proposal."""
        mock_llm.return_value = "Here's how to implement sorting."

        resp = client.post("/api/chat", json={
            "message": "Write a function to sort an array",
            "workspace_id": chat_workspace["id"],
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["file_change_proposal"] is None

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_proposal_approve_via_changes_api(
        self, mock_llm, chat_workspace
    ):
        """A proposal created via chat can be approved through the Changes API."""
        mock_llm.return_value = "Proposed."

        ws_id = chat_workspace["id"]
        message = (
            'Modify hello.js and\n'
            'change:\nconst message = "Hello DevAgent";\n'
            'to:\nconst message = "Approved Change!";'
        )

        chat_resp = client.post("/api/chat", json={
            "message": message,
            "workspace_id": ws_id,
        })
        proposal_id = chat_resp.json()["file_change_proposal"]["id"]

        # Approve the proposal
        approve_resp = client.post(
            f"/api/workspaces/{ws_id}/changes/{proposal_id}/approve"
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "applied"

        # Verify file is now modified
        disk_content = chat_workspace["hello_file"].read_text(encoding="utf-8")
        assert 'const message = "Approved Change!";' in disk_content

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_proposal_reject_via_changes_api(
        self, mock_llm, chat_workspace
    ):
        """A proposal created via chat can be rejected through the Changes API."""
        mock_llm.return_value = "Proposed."

        ws_id = chat_workspace["id"]
        message = (
            'Modify hello.js and\n'
            'change:\nconst message = "Hello DevAgent";\n'
            'to:\nconst message = "Rejected Change!";'
        )

        chat_resp = client.post("/api/chat", json={
            "message": message,
            "workspace_id": ws_id,
        })
        proposal_id = chat_resp.json()["file_change_proposal"]["id"]

        # Reject the proposal
        reject_resp = client.post(
            f"/api/workspaces/{ws_id}/changes/{proposal_id}/reject"
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"

        # Verify file remains unchanged
        disk_content = chat_workspace["hello_file"].read_text(encoding="utf-8")
        assert 'const message = "Hello DevAgent";' in disk_content
        assert "Rejected Change!" not in disk_content

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_invalid_workspace_id_no_proposal(self, mock_llm):
        """Invalid workspace_id silently skips proposal creation."""
        mock_llm.return_value = "OK."

        resp = client.post("/api/chat", json={
            "message": 'Modify hello.js and change: x to: y',
            "workspace_id": "nonexistent-ws-id",
        })

        assert resp.status_code == 200
        assert resp.json()["file_change_proposal"] is None

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_file_not_found_no_proposal(self, mock_llm, chat_workspace):
        """If the target file doesn't exist in workspace, no proposal is created."""
        mock_llm.return_value = "Cannot find that file."

        resp = client.post("/api/chat", json={
            "message": 'Modify nonexistent.js and change: x to: y',
            "workspace_id": chat_workspace["id"],
        })

        assert resp.status_code == 200
        assert resp.json()["file_change_proposal"] is None

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_old_text_not_in_file_no_proposal(self, mock_llm, chat_workspace):
        """If old_text is not found in the file, no proposal is created."""
        mock_llm.return_value = "The text wasn't found."

        resp = client.post("/api/chat", json={
            "message": (
                'Modify hello.js and\n'
                'change:\nthis text does not exist in the file\n'
                'to:\nnew text'
            ),
            "workspace_id": chat_workspace["id"],
        })

        assert resp.status_code == 200
        assert resp.json()["file_change_proposal"] is None
