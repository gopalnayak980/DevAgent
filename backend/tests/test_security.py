"""
Tests for Phase 10.1: Security Foundation.
"""

import pytest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


class TestSecurityFeatures:
    """Test security middleware, limits, and safe error handling."""

    def test_security_headers_present(self):
        """Verify that basic security headers are added to responses."""
        response = client.get("/")
        assert response.status_code == 200
        
        headers = response.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert "content-security-policy" in headers

    def test_chat_message_too_long(self):
        """Verify that an oversized message is rejected with a 400 error."""
        oversized_message = "a" * (settings.MAX_MESSAGE_LENGTH + 1)
        response = client.post(
            "/api/chat",
            json={"message": oversized_message},
        )
        assert response.status_code == 400
        assert "exceeds maximum length" in response.json()["detail"]

    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    def test_chat_message_valid_length(self, mock_llm):
        """Verify that a valid message is processed."""
        mock_llm.return_value = "Test response"
        valid_message = "a" * 10
        response = client.post(
            "/api/chat",
            json={"message": valid_message},
        )
        assert response.status_code == 200

    def test_rate_limiter_middleware(self):
        """Verify that rate limiting blocks excessive requests."""
        limit = settings.RATE_LIMIT_REQUESTS
        
        # Use a unique IP for this test to avoid polluting the rate limiter for other tests
        headers = {"X-Forwarded-For": "192.168.1.99"}
        
        for _ in range(limit):
            response = client.post(
                "/api/jobs",
                json={"message": "test", "job_type": "agent_task"},
                headers=headers
            )
            assert response.status_code in (202, 429)

        response = client.post(
            "/api/jobs",
            json={"message": "test", "job_type": "agent_task"},
            headers=headers
        )
        assert response.status_code == 429
        assert "Too many requests" in response.json()["detail"]

    def test_request_size_middleware(self):
        """Verify that overly large request bodies are rejected."""
        # A 2MB string
        large_body = "a" * (2 * 1024 * 1024)
        
        response = client.post(
            "/api/chat",
            content=f'{{"message": "{large_body}"}}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()
