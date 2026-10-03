"""
Tests for Phase 6 — Human-in-the-Loop (HITL) Approval Workflow.

Covers:
1. Creating approval request
2. Getting approval request
3. Listing approvals
4. Approving pending request
5. Rejecting pending request
6. Cancelling request
7. Invalid state transitions
8. AI cannot self-approve (approval only via explicit API action)
9. Protected action does not execute while pending
10. Protected action executes only after approval
11. Chat integration — protected action triggers approval
12. Chat integration — normal messages flow through unchanged
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.models import ApprovalRequest
from app.hitl.repository import ApprovalRepository
from app.hitl.service import (
    HumanApprovalService,
    ApprovalNotFoundError,
    InvalidTransitionError,
)


client = TestClient(app)


# ===========================================================================
# 1. Creating approval request
# ===========================================================================

class TestCreateApproval:
    """Test creating approval requests via API."""

    def test_create_approval_returns_201(self):
        response = client.post(
            "/api/approvals",
            json={
                "action_type": "demo_protected_action",
                "description": "Run the demo protected action.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["action_type"] == "demo_protected_action"
        assert data["description"] == "Run the demo protected action."
        assert "id" in data
        assert "created_at" in data

    def test_create_approval_missing_fields_returns_422(self):
        response = client.post("/api/approvals", json={})
        assert response.status_code == 422

    def test_create_approval_empty_action_type_returns_422(self):
        response = client.post(
            "/api/approvals",
            json={"action_type": "", "description": "Some action."},
        )
        assert response.status_code == 422


# ===========================================================================
# 2. Getting approval request
# ===========================================================================

class TestGetApproval:
    """Test retrieving a single approval request."""

    def test_get_existing_approval(self):
        # Create first
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "test_action", "description": "Test action."},
        )
        approval_id = create_resp.json()["id"]

        # Get
        response = client.get(f"/api/approvals/{approval_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == approval_id
        assert data["status"] == "pending"

    def test_get_nonexistent_approval_returns_404(self):
        response = client.get("/api/approvals/nonexistent-id")
        assert response.status_code == 404


# ===========================================================================
# 3. Listing approvals
# ===========================================================================

class TestListApprovals:
    """Test listing approval requests."""

    def test_list_approvals_returns_list(self):
        # Create a couple
        client.post(
            "/api/approvals",
            json={"action_type": "action1", "description": "First."},
        )
        client.post(
            "/api/approvals",
            json={"action_type": "action2", "description": "Second."},
        )

        response = client.get("/api/approvals")
        assert response.status_code == 200
        data = response.json()
        assert "approvals" in data
        assert "total" in data
        assert data["total"] >= 2


# ===========================================================================
# 4. Approving pending request
# ===========================================================================

class TestApproveRequest:
    """Test approving a pending approval request."""

    def test_approve_pending_request(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "demo_protected_action", "description": "Approve me."},
        )
        approval_id = create_resp.json()["id"]

        response = client.post(f"/api/approvals/{approval_id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["id"] == approval_id
        # The demo action should have executed
        assert "executed successfully" in data["message"]

    def test_approve_nonexistent_returns_404(self):
        response = client.post("/api/approvals/nonexistent-id/approve")
        assert response.status_code == 404


# ===========================================================================
# 5. Rejecting pending request
# ===========================================================================

class TestRejectRequest:
    """Test rejecting a pending approval request."""

    def test_reject_pending_request(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "demo_protected_action", "description": "Reject me."},
        )
        approval_id = create_resp.json()["id"]

        response = client.post(f"/api/approvals/{approval_id}/reject")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert "not executed" in data["message"]

    def test_reject_nonexistent_returns_404(self):
        response = client.post("/api/approvals/nonexistent-id/reject")
        assert response.status_code == 404


# ===========================================================================
# 6. Cancelling request
# ===========================================================================

class TestCancelRequest:
    """Test cancelling a pending approval request."""

    def test_cancel_pending_request(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "demo_protected_action", "description": "Cancel me."},
        )
        approval_id = create_resp.json()["id"]

        response = client.post(f"/api/approvals/{approval_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_nonexistent_returns_404(self):
        response = client.post("/api/approvals/nonexistent-id/cancel")
        assert response.status_code == 404


# ===========================================================================
# 7. Invalid state transitions
# ===========================================================================

class TestInvalidTransitions:
    """Test that invalid state transitions are properly rejected."""

    def test_cannot_approve_already_approved(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "test", "description": "Double approve."},
        )
        approval_id = create_resp.json()["id"]

        # First approve
        client.post(f"/api/approvals/{approval_id}/approve")

        # Try to approve again
        response = client.post(f"/api/approvals/{approval_id}/approve")
        assert response.status_code == 400

    def test_cannot_reject_already_approved(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "test", "description": "Approve then reject."},
        )
        approval_id = create_resp.json()["id"]

        client.post(f"/api/approvals/{approval_id}/approve")

        response = client.post(f"/api/approvals/{approval_id}/reject")
        assert response.status_code == 400

    def test_cannot_approve_already_rejected(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "test", "description": "Reject then approve."},
        )
        approval_id = create_resp.json()["id"]

        client.post(f"/api/approvals/{approval_id}/reject")

        response = client.post(f"/api/approvals/{approval_id}/approve")
        assert response.status_code == 400

    def test_cannot_approve_already_cancelled(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "test", "description": "Cancel then approve."},
        )
        approval_id = create_resp.json()["id"]

        client.post(f"/api/approvals/{approval_id}/cancel")

        response = client.post(f"/api/approvals/{approval_id}/approve")
        assert response.status_code == 400

    def test_cannot_reject_already_cancelled(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "test", "description": "Cancel then reject."},
        )
        approval_id = create_resp.json()["id"]

        client.post(f"/api/approvals/{approval_id}/cancel")

        response = client.post(f"/api/approvals/{approval_id}/reject")
        assert response.status_code == 400

    def test_cannot_cancel_already_approved(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "test", "description": "Approve then cancel."},
        )
        approval_id = create_resp.json()["id"]

        client.post(f"/api/approvals/{approval_id}/approve")

        response = client.post(f"/api/approvals/{approval_id}/cancel")
        assert response.status_code == 400


# ===========================================================================
# 8. AI cannot self-approve
# ===========================================================================

class TestAICannotSelfApprove:
    """Verify that the AI/system can only create approval requests,
    not directly approve them. Approval must come through the explicit
    /approve API endpoint (user action)."""

    @pytest.mark.asyncio
    async def test_service_create_does_not_auto_approve(self, setup_test_db):
        """Creating an approval via the service always sets status=pending."""
        session = setup_test_db
        repo = ApprovalRepository(session)
        service = HumanApprovalService(repo)

        approval = await service.create_approval(
            user_id="ai-user",
            action_type="demo_protected_action",
            description="AI created this.",
        )
        assert approval.status == "pending"
        # There's no way to pass status="approved" through create_approval

    @pytest.mark.asyncio
    async def test_service_has_no_force_approve_method(self, setup_test_db):
        """The service does not expose a method to bypass the state machine."""
        service = HumanApprovalService(ApprovalRepository(setup_test_db))
        # The only way to approve is through the approve() method,
        # which requires an explicit call (mapped to an API endpoint)
        assert not hasattr(service, "force_approve")
        assert not hasattr(service, "auto_approve")


# ===========================================================================
# 9. Protected action does not execute while pending
# ===========================================================================

class TestProtectedActionPending:
    """Verify the demo protected action cannot execute while pending."""

    @pytest.mark.asyncio
    async def test_execute_while_pending_returns_false(self, setup_test_db):
        session = setup_test_db
        repo = ApprovalRepository(session)
        service = HumanApprovalService(repo)

        approval = await service.create_approval(
            user_id="test-user",
            action_type="demo_protected_action",
            description="Should not execute.",
        )

        result = await service.execute_if_approved(approval.id)
        assert result["executed"] is False
        assert "pending" in result["result"]

    @pytest.mark.asyncio
    async def test_execute_while_rejected_returns_false(self, setup_test_db):
        session = setup_test_db
        repo = ApprovalRepository(session)
        service = HumanApprovalService(repo)

        approval = await service.create_approval(
            user_id="test-user",
            action_type="demo_protected_action",
            description="Should not execute after rejection.",
        )
        await service.reject(approval.id)

        result = await service.execute_if_approved(approval.id)
        assert result["executed"] is False

    def test_execute_endpoint_rejects_pending(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "demo_protected_action", "description": "Pending."},
        )
        approval_id = create_resp.json()["id"]

        response = client.post(f"/api/approvals/{approval_id}/execute")
        assert response.status_code == 400


# ===========================================================================
# 10. Protected action executes only after approval
# ===========================================================================

class TestProtectedActionAfterApproval:
    """Verify the demo protected action executes after approval."""

    @pytest.mark.asyncio
    async def test_execute_after_approval_returns_true(self, setup_test_db):
        session = setup_test_db
        repo = ApprovalRepository(session)
        service = HumanApprovalService(repo)

        approval = await service.create_approval(
            user_id="test-user",
            action_type="demo_protected_action",
            description="Should execute after approval.",
        )
        await service.approve(approval.id)

        result = await service.execute_if_approved(approval.id)
        assert result["executed"] is True
        assert "executed successfully" in result["result"]

    def test_execute_endpoint_succeeds_after_approval(self):
        create_resp = client.post(
            "/api/approvals",
            json={"action_type": "demo_protected_action", "description": "Execute me."},
        )
        approval_id = create_resp.json()["id"]

        # Approve first
        client.post(f"/api/approvals/{approval_id}/approve")

        # Execute
        response = client.post(f"/api/approvals/{approval_id}/execute")
        assert response.status_code == 200
        data = response.json()
        assert data["executed"] is True


# ===========================================================================
# 11. Chat integration — protected action triggers HITL
# ===========================================================================

class TestChatHITLIntegration:
    """Verify that the chat endpoint triggers HITL for protected actions."""

    def test_protected_action_message_creates_approval(self):
        response = client.post(
            "/api/chat",
            json={"message": "Run the demo protected action"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_approval"] is True
        assert data["approval"] is not None
        assert data["approval"]["status"] == "pending"
        assert data["approval"]["action_type"] == "demo_protected_action"
        assert "approval" in data["response"].lower() or "⚠️" in data["response"]

    def test_protected_action_with_varied_phrasing(self):
        """Different phrasings should all trigger HITL."""
        messages = [
            "Execute the protected action",
            "Run the demo protected action please",
            "Trigger the protected action now",
            "Perform the demo protected action",
            "Run the protected demo action", # The runtime bug phrase
        ]
        for msg in messages:
            response = client.post("/api/chat", json={"message": msg})
            assert response.status_code == 200
            data = response.json()
            assert data.get("requires_approval") is True, f"Failed for message: {msg}"


# ===========================================================================
# 12. Normal messages still flow through unchanged
# ===========================================================================

class TestChatNormalFlow:
    """Verify that normal messages are not affected by HITL."""

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_normal_coding_message_not_hitl(self, mock_llm):
        mock_llm.return_value = "Here is the function."
        response = client.post(
            "/api/chat",
            json={"message": "Write a Python function to add two numbers"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("requires_approval", False) is False
        assert data["response"] == "Here is the function."

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_normal_learning_message_not_hitl(self, mock_llm):
        mock_llm.return_value = "Inheritance in Java means..."
        response = client.post(
            "/api/chat",
            json={"message": "Explain Java inheritance"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("requires_approval", False) is False

    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    def test_calculator_message_not_hitl(self, mock_llm):
        mock_llm.return_value = "25 * 30 is 750."
        response = client.post(
            "/api/chat",
            json={"message": "Calculate 25 * 30"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("requires_approval", False) is False
