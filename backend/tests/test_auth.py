"""
Authentication API tests.

Tests user registration, login, JWT validation, duplicate checks,
and profile retrieval.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "new@test.edu",
        "username": "newuser",
        "password": "SecurePass123!",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.edu"
    assert data["username"] == "newuser"
    assert data["role"] == "student"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    """Test registration fails with duplicate email."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "student@test.edu",  # Same as test_user
        "username": "different",
        "password": "SecurePass123!",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user: User):
    """Test registration fails with duplicate username."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "different@test.edu",
        "username": "teststudent",  # Same as test_user
        "password": "SecurePass123!",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration fails with invalid email format."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "username": "someone",
        "password": "SecurePass123!",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test registration fails with password under 8 characters."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "short@test.edu",
        "username": "shortpw",
        "password": "abc",
    })
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Test successful login returns a JWT token."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "student@test.edu",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User):
    """Test login fails with incorrect password."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "student@test.edu",
        "password": "WrongPassword!",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login fails for non-existent email."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.edu",
        "password": "SomePass123!",
    })
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Profile tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test retrieving profile with valid JWT."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "student@test.edu"
    assert data["username"] == "teststudent"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """Test profile endpoint rejects requests without JWT."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    """Test profile endpoint rejects invalid JWT."""
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
