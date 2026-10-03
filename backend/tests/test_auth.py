import pytest
from httpx import AsyncClient
from app.main import app
from app.auth.dependencies import get_current_active_user, require_admin

@pytest.mark.asyncio
async def test_auth_registration():
    # Remove overrides for auth tests
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]
    if require_admin in app.dependency_overrides:
        del app.dependency_overrides[require_admin]
        
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user
        res = await client.post("/api/auth/register", json={
            "name": "Bob",
            "email": "Bob@Example.com",
            "password": "password123",
            "confirm_password": "password123"
        })
        assert res.status_code == 201
        data = res.json()
        assert data["user"]["email"] == "bob@example.com"
        assert "password_hash" not in data["user"]
        assert "access_token" in data
        
        # Duplicate register
        res2 = await client.post("/api/auth/register", json={
            "name": "Bob",
            "email": "Bob@example.com",
            "password": "password123",
            "confirm_password": "password123"
        })
        assert res2.status_code == 409
        
        # Login
        login_res = await client.post("/api/auth/login", json={
            "email": "bob@example.com",
            "password": "password123"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        
        # Get me
        me_res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "bob@example.com"
        
        # Unauthorized access
        unauth_res = await client.get("/api/auth/me")
        assert unauth_res.status_code == 401
