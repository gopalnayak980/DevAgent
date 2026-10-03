"""
Tests for the observability endpoints and service — Phase 8.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.models import ExecutionTrace, User
from app.auth.dependencies import get_current_active_user, require_admin

@pytest_asyncio.fixture
async def sample_trace(setup_test_db):
    """Fixture to create a sample completed execution trace for test-user-id."""
    trace = ExecutionTrace(
        user_id="test-user-id",
        task_type="coding",
        agent_name="Coding Specialist",
        status="completed",
        duration_ms=1250.5,
        llm_call_count=2,
        tool_call_count=1
    )
    trace.set_tools_used(["calculator"])
    
    setup_test_db.add(trace)
    await setup_test_db.commit()
    await setup_test_db.refresh(trace)
    return trace

@pytest_asyncio.fixture
async def other_user_trace(setup_test_db):
    """Fixture to create a trace for a different user."""
    trace = ExecutionTrace(
        user_id="other-user",
        task_type="debugging",
        agent_name="Debugging Specialist",
        status="completed",
        duration_ms=500.0,
        error_message="None"
    )
    setup_test_db.add(trace)
    await setup_test_db.commit()
    await setup_test_db.refresh(trace)
    return trace

@pytest_asyncio.fixture
def override_normal_user():
    def _override():
        return User(id="test-user-id", role="user", is_active=True, email="user@test.com")
    app.dependency_overrides[get_current_active_user] = _override
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
def override_unauth_user():
    def _override():
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    app.dependency_overrides[get_current_active_user] = _override
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestObservabilityEndpoints:
    
    async def test_normal_user_can_read_own_traces(self, sample_trace, other_user_trace, override_normal_user):
        """Test GET /api/observability/traces returns only own traces for normal users."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/observability/traces")
        
        assert response.status_code == 200
        data = response.json()
        traces = data["traces"]
        
        trace_ids = [t["id"] for t in traces]
        assert sample_trace.id in trace_ids
        assert other_user_trace.id not in trace_ids

    async def test_normal_user_cannot_read_another_users_trace(self, other_user_trace, override_normal_user):
        """Test GET /api/observability/traces/{id} denies access for traces they don't own."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/observability/traces/{other_user_trace.id}")
        
        assert response.status_code == 403

    async def test_normal_user_stats_contain_only_own_executions(self, sample_trace, other_user_trace, override_normal_user):
        """Test GET /api/observability/stats returns aggregate metrics for own executions only."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/observability/stats")
            
        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 1  # Only the sample_trace
        assert data["total_llm_calls"] == 2

    async def test_admin_can_access_broader_observability_data(self, sample_trace, other_user_trace):
        """Test GET /api/observability/traces returns all traces for admin."""
        # By default in conftest, the user is an admin
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/observability/traces")
        
        assert response.status_code == 200
        data = response.json()
        trace_ids = [t["id"] for t in data["traces"]]
        assert sample_trace.id in trace_ids
        assert other_user_trace.id in trace_ids
        
    async def test_unauthenticated_access_remains_rejected(self, override_unauth_user):
        """Test GET /api/observability/traces returns 401 for unauthenticated requests."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/observability/traces")
            
        assert response.status_code == 401
