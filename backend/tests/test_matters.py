"""Integration tests for the /api/v1/matters endpoints.

Covers matter CRUD, membership management, and the ethical-wall access
control that prevents users from seeing matters they are not assigned to.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MatterMembership, UserRole
from tests.conftest import auth_headers, make_user

# ---------------------------------------------------------------------------
# POST /matters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_matter_as_partner(async_client: AsyncClient, partner) -> None:
    """Partners can create matters; the creator is auto-added as a member."""
    response = await async_client.post(
        "/api/v1/matters",
        headers=auth_headers(partner),
        json={
            "name": "Smith v. Jones",
            "description": "IP dispute",
            "client_name": "Smith Corp",
            "jurisdiction": "SDNY",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Smith v. Jones"
    assert body["client_name"] == "Smith Corp"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_create_matter_as_associate(async_client: AsyncClient, associate) -> None:
    """Associates cannot create matters."""
    response = await async_client.post(
        "/api/v1/matters",
        headers=auth_headers(associate),
        json={"name": "Sneaky Matter", "client_name": "Client"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /matters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_matters_returns_only_accessible(
    async_client: AsyncClient,
    partner,
    associate,
    matter,
    test_db: AsyncSession,
) -> None:
    """Each user only sees matters they are a member of."""
    # partner is in 'matter'; associate is not
    partner_resp = await async_client.get("/api/v1/matters", headers=auth_headers(partner))
    assert partner_resp.status_code == 200
    partner_ids = [m["id"] for m in partner_resp.json()]
    assert matter.id in partner_ids

    associate_resp = await async_client.get("/api/v1/matters", headers=auth_headers(associate))
    assert associate_resp.status_code == 200
    associate_ids = [m["id"] for m in associate_resp.json()]
    assert matter.id not in associate_ids


@pytest.mark.asyncio
async def test_list_matters_unauthenticated(async_client: AsyncClient) -> None:
    """Unauthenticated request is rejected (HTTPBearer returns 403)."""
    response = await async_client.get("/api/v1/matters")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /matters/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_matter_as_member(async_client: AsyncClient, partner, matter) -> None:
    """A member can retrieve matter details including the members list."""
    response = await async_client.get(
        f"/api/v1/matters/{matter.id}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == matter.id
    member_emails = [m["email"] for m in body["members"]]
    assert "partner@firm.com" in member_emails


@pytest.mark.asyncio
async def test_get_matter_denied_for_non_member(
    async_client: AsyncClient, associate, matter
) -> None:
    """Non-members receive 403 — the ethical wall is enforced."""
    response = await async_client.get(
        f"/api/v1/matters/{matter.id}",
        headers=auth_headers(associate),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_matter_not_found(async_client: AsyncClient, partner) -> None:
    """Non-existent matter ID returns 403 (access gate fires before DB lookup)."""
    response = await async_client.get(
        f"/api/v1/matters/{uuid.uuid4()}",
        headers=auth_headers(partner),
    )
    # The check_matter_access dependency fires first → 403
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /matters/{id}/members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_member(async_client: AsyncClient, partner, associate, matter) -> None:
    """Partner can add a user to a matter."""
    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/members",
        headers=auth_headers(partner),
        json={"user_id": associate.id},
    )
    assert response.status_code == 201
    assert response.json()["message"] == "User added to matter successfully"


@pytest.mark.asyncio
async def test_add_member_duplicate(async_client: AsyncClient, partner, matter) -> None:
    """Adding an already-existing member returns 409."""
    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/members",
        headers=auth_headers(partner),
        json={"user_id": partner.id},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_add_member_user_not_found(async_client: AsyncClient, partner, matter) -> None:
    """Adding a non-existent user returns 404."""
    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/members",
        headers=auth_headers(partner),
        json={"user_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_member_as_associate_forbidden(
    async_client: AsyncClient, associate, matter, test_db: AsyncSession
) -> None:
    """Associates cannot manage matter membership."""
    # First give associate access to the matter
    test_db.add(
        MatterMembership(
            id=str(uuid.uuid4()),
            user_id=associate.id,
            matter_id=matter.id,
            granted_by=associate.id,
        )
    )
    await test_db.commit()

    third = await make_user(test_db, email="third@firm.com", role=UserRole.ASSOCIATE)
    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/members",
        headers=auth_headers(associate),
        json={"user_id": third.id},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /matters/{id}/members/{user_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_member(
    async_client: AsyncClient, partner, associate, matter, test_db: AsyncSession
) -> None:
    """Partner can remove a member that is not the last one."""
    # Add associate to matter first
    test_db.add(
        MatterMembership(
            id=str(uuid.uuid4()),
            user_id=associate.id,
            matter_id=matter.id,
            granted_by=partner.id,
        )
    )
    await test_db.commit()

    response = await async_client.delete(
        f"/api/v1/matters/{matter.id}/members/{associate.id}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User removed from matter"


@pytest.mark.asyncio
async def test_cannot_remove_last_member(async_client: AsyncClient, partner, matter) -> None:
    """Removing the last member of a matter is blocked."""
    response = await async_client.delete(
        f"/api/v1/matters/{matter.id}/members/{partner.id}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_remove_member_not_found(
    async_client: AsyncClient, partner, associate, matter
) -> None:
    """Removing a user who is not a member returns 404."""
    response = await async_client.delete(
        f"/api/v1/matters/{matter.id}/members/{associate.id}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 404
