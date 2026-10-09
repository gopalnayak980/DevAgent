"""
Tests for Phase 10: Dynamic Conversation IDs in the chat API.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.models import Conversation
from app.auth.dependencies import get_current_active_user
from app.database.models import User

client = TestClient(app)


class TestConversationIDs:
    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    def test_chat_creates_new_conversation(self, mock_llm, mock_llm_prompts):
        mock_llm.return_value = "Hello"
        mock_llm_prompts.return_value = "Hello"
        
        response = client.post("/api/chat", json={"message": "Hi"})
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert data["conversation_id"] is not None
        
    @patch("app.routes.chat.get_llm_response_with_prompts", new_callable=AsyncMock)
    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    def test_chat_continues_conversation(self, mock_llm, mock_llm_prompts):
        mock_llm.return_value = "Hello"
        mock_llm_prompts.return_value = "Hello"
        
        # Create
        response1 = client.post("/api/chat", json={"message": "Hi"})
        conv_id = response1.json()["conversation_id"]
        
        # Continue
        response2 = client.post("/api/chat", json={"message": "Hi", "conversation_id": conv_id})
        assert response2.status_code == 200
        assert response2.json()["conversation_id"] == conv_id

    @pytest.mark.asyncio
    @patch("app.routes.chat.get_llm_response", new_callable=AsyncMock)
    async def test_chat_denies_access_to_other_users_conversation(self, mock_llm, setup_test_db):
        # setup_test_db is the AsyncSession from conftest — use it directly
        session = setup_test_db
        
        # Manually insert a conversation owned by a different user
        other_conv_id = "fake-other-user-conv-id"
        other_conv = Conversation(id=other_conv_id, user_id="some-other-user")
        session.add(other_conv)
        await session.commit()
        
        # The test user ("test-user-id" from conftest) must be denied access
        response = client.post("/api/chat", json={"message": "Hi", "conversation_id": other_conv_id})
        assert response.status_code == 403
        assert "Conversation not found or access denied" in response.json()["detail"]
