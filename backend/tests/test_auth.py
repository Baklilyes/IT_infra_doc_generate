import pytest
from httpx import AsyncClient
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

@pytest.mark.asyncio
async def test_password_hashing():
    pwd = "SecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

@pytest.mark.asyncio
async def test_jwt_token_creation_and_decoding():
    payload = {"sub": "user-123", "role": "engineer"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123"
    assert decoded["role"] == "engineer"

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_users):
    resp = await client.post("/api/auth/login", json={
        "username": "admin_test",
        "password": "AdminPass123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin_test"
    assert data["user"]["role"] == "administrator"

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_users):
    resp = await client.post("/api/auth/login", json={
        "username": "admin_test",
        "password": "WrongPassword!"
    })
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, test_users):
    resp = await client.post("/api/auth/login", json={
        "username": "inactive_test",
        "password": "InactivePass123!"
    })
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "eng_test"
    assert data["role"] == "engineer"

@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_admin_create_user_success(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    resp = await client.post("/api/auth/users", headers=headers, json={
        "username": "new_lead",
        "email": "new_lead@example.com",
        "full_name": "New Technical Lead",
        "role": "technical_lead",
        "password": "SecurePassword123!"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "new_lead"
    assert data["role"] == "technical_lead"

@pytest.mark.asyncio
async def test_engineer_cannot_create_user(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    resp = await client.post("/api/auth/users", headers=headers, json={
        "username": "hacker_user",
        "email": "hacker@example.com",
        "full_name": "Hacker User",
        "role": "administrator",
        "password": "Password123!"
    })
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    resp = await client.get("/api/auth/users", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4

@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert "components" in data
    assert data["components"]["backend"]["status"] == "operational"
