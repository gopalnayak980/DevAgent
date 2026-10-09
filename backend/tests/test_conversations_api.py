"""
Tests for Conversation History APIs.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.models import Conversation, Message

client = TestClient(app)


class TestConversationHistoryAPI:
    @pytest.mark.asyncio
    async def test_list_own_conversations(self, setup_test_db):
        session = setup_test_db

        # Create a conversation for the test user ('test-user-id' from conftest)
        c1 = Conversation(id="conv-1", user_id="test-user-id")
        # Create a conversation for another user — must NOT appear in response
        c2 = Conversation(id="conv-2", user_id="other-user")
        session.add(c1)
        session.add(c2)
        await session.commit()

        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "conv-1"
        assert "title" in data[0]

    @pytest.mark.asyncio
    async def test_get_own_conversation_messages(self, setup_test_db):
        session = setup_test_db

        c1 = Conversation(id="conv-3", user_id="test-user-id")
        m1 = Message(conversation_id="conv-3", role="user", content="hello")
        m2 = Message(conversation_id="conv-3", role="assistant", content="hi")
        session.add_all([c1, m1, m2])
        await session.commit()

        response = client.get("/api/conversations/conv-3/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["content"] == "hello"
        assert data[1]["content"] == "hi"

    @pytest.mark.asyncio
    async def test_cannot_get_other_user_conversation_messages(self, setup_test_db):
        session = setup_test_db

        c1 = Conversation(id="conv-4", user_id="other-user")
        m1 = Message(conversation_id="conv-4", role="user", content="hello")
        session.add_all([c1, m1])
        await session.commit()

        response = client.get("/api/conversations/conv-4/messages")
        assert response.status_code == 403
        assert "Conversation not found or access denied" in response.json()["detail"]

    def test_unauthenticated_requests_rejected(self):
        from app.auth.dependencies import get_current_active_user

        # Temporarily remove the auth override to simulate unauthenticated requests
        override = app.dependency_overrides.get(get_current_active_user)
        app.dependency_overrides.pop(get_current_active_user, None)

        try:
            response = client.get("/api/conversations")
            assert response.status_code == 401

            response = client.get("/api/conversations/some-id/messages")
            assert response.status_code == 401
        finally:
            if override:
                app.dependency_overrides[get_current_active_user] = override
