"""
Tests for the observability endpoints and service — Phase 8.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.models import ExecutionTrace

@pytest_asyncio.fixture
async def sample_trace(setup_test_db):
    """Fixture to create a sample completed execution trace."""
    trace = ExecutionTrace(
        user_id="user-123",
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
async def failed_trace(setup_test_db):
    """Fixture to create a sample failed execution trace."""
    trace = ExecutionTrace(
        user_id="user-123",
        task_type="debugging",
        agent_name="Debugging Specialist",
        status="failed",
        duration_ms=500.0,
        error_message="Connection timed out"
    )
    setup_test_db.add(trace)
    await setup_test_db.commit()
    await setup_test_db.refresh(trace)
    return trace

@pytest.mark.asyncio
class TestObservabilityEndpoints:
    
    async def test_list_traces(self, sample_trace, failed_trace):
        """Test GET /api/observability/traces returns the list of traces."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/observability/traces")
        
        assert response.status_code == 200
        data = response.json()
        assert "traces" in data
        assert data["total"] >= 2
        
        traces = data["traces"]
        trace_ids = [t["id"] for t in traces]
        assert sample_trace.id in trace_ids
        assert failed_trace.id in trace_ids

    async def test_get_trace_by_id(self, sample_trace):
        """Test GET /api/observability/traces/{id} returns the specific trace."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/observability/traces/{sample_trace.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_trace.id
        assert data["task_type"] == "coding"
        assert data["agent_name"] == "Coding Specialist"
        assert data["status"] == "completed"
        assert data["duration_ms"] == 1250.5
        assert data["llm_call_count"] == 2
        assert data["tool_call_count"] == 1
        assert "calculator" in data["tools_used"]

    async def test_get_trace_not_found(self):
        """Test GET /api/observability/traces/{id} for non-existent ID returns 404."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/observability/traces/nonexistent-id-123")
        
        assert response.status_code == 404

    async def test_get_observability_stats(self, sample_trace, failed_trace):
        """Test GET /api/observability/stats returns aggregate metrics."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/observability/stats")
            
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_executions"] >= 2
        assert data["successful_executions"] >= 1
        assert data["failed_executions"] >= 1
        assert data["total_llm_calls"] >= 2
        assert data["total_tool_calls"] >= 1
        assert data["average_duration_ms"] is not None
