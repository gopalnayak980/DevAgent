"""
Tests for main application endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_health():
    """Verify that the health check endpoint returns expected output."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "DevAgent backend"
    }
