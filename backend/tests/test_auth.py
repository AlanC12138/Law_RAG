"""Integration tests for the /api/v1/auth endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.db.models import UserRole


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, associate) -> None:
    """Valid credentials return access + refresh tokens."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "associate@firm.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, associate) -> None:
    """Wrong password returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "associate@firm.com", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(async_client: AsyncClient) -> None:
    """Non-existent email returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@firm.com", "password": "password123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(
    async_client: AsyncClient, test_db: AsyncSession
) -> None:
    """Disabled accounts are rejected with 403."""
    inactive = await make_user(
        test_db,
        email="inactive@firm.com",
        role=UserRole.ASSOCIATE,
        is_active=False,
    )
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": inactive.email, "password": "password123"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient, associate) -> None:
    """Authenticated user receives their own profile."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers=auth_headers(associate),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "associate@firm.com"
    assert body["role"] == "associate"


@pytest.mark.asyncio
async def test_get_me_no_token(async_client: AsyncClient) -> None:
    """Request without a token is rejected — FastAPI HTTPBearer returns 403."""
    response = await async_client.get("/api/v1/auth/me")
    # HTTPBearer raises 403 when Authorization header is absent
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_invalid_token(async_client: AsyncClient) -> None:
    """Malformed token returns 401."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient, associate) -> None:
    """Logout endpoint acknowledges the request."""
    response = await async_client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(associate),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"
