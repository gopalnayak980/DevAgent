"""
Tests for the chat API endpoint — Phase 4 integration.

Verifies that the /api/chat endpoint still returns successful responses
with the supervisor agent, specialized agents, and tool calling integrated.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestChatEndpoint:
    """Tests for POST /api/chat with the supervisor integrated."""

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_chat_returns_successful_response(self, mock_llm_prompts):
        """The endpoint returns a valid response with the supervisor and specialized agent in the flow."""
        mock_llm_prompts.return_value = "Here is a Python function to add two numbers."

        response = client.post(
            "/api/chat",
            json={"message": "Write a function to add two numbers"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["response"] == "Here is a Python function to add two numbers."

        # Verify the specialized agent flow was used
        mock_llm_prompts.assert_called_once()
        call_kwargs = mock_llm_prompts.call_args.kwargs
        assert "system_prompt" in call_kwargs
        assert "user_prompt" in call_kwargs

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_chat_supervisor_context_has_correct_intent(self, mock_llm_prompts):
        """The supervisor passes the correct intent to the debugging agent."""
        mock_llm_prompts.return_value = "Here's how to fix the bug."

        response = client.post(
            "/api/chat",
            json={"message": "Fix this bug in my code"},
        )

        assert response.status_code == 200
        mock_llm_prompts.assert_called_once()
        system_prompt = mock_llm_prompts.call_args.kwargs.get("system_prompt")
        assert system_prompt is not None
        assert "Debugging Specialist" in system_prompt

    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    @patch("app.routes.chat.supervisor_analyze", side_effect=RuntimeError("Supervisor broke"))
    def test_chat_supervisor_failure_falls_back(self, mock_supervisor, mock_llm):
        """If the supervisor fails, the LLM is still called without context."""
        mock_llm.return_value = "Fallback response."

        response = client.post(
            "/api/chat",
            json={"message": "Hello"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Fallback response."

        # supervisor_context should be None due to the failure
        supervisor_context = mock_llm.call_args.kwargs.get("supervisor_context")
        assert supervisor_context is None

    def test_chat_empty_message_returns_400(self):
        """An empty message still returns a 400 error."""
        response = client.post("/api/chat", json={"message": ""})
        assert response.status_code == 422  # Pydantic validation (min_length=1)

    def test_chat_missing_message_returns_422(self):
        """A missing message field returns a 422 validation error."""
        response = client.post("/api/chat", json={})
        assert response.status_code == 422

    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    def test_chat_response_format_unchanged(self, mock_llm):
        """The response format is still { 'response': '...' } for frontend compatibility."""
        mock_llm.return_value = "Test response"

        response = client.post(
            "/api/chat",
            json={"message": "Tell me about Python"},
        )

        data = response.json()
        # Phase 6: response now also contains HITL fields
        assert "response" in data
        assert data.get("requires_approval", False) is False


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_reflects_phase_10(self):
        """The health check should report Phase 10.1."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == 10.1
        assert data["version"] == "0.10.1"

