from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import check_matter_access, get_current_active_user, require_partner
from app.db.models import Document, Matter, MatterMembership, QueryLog, User
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matters", tags=["matters"])


class MatterCreate(BaseModel):
    """Matter creation request."""

    name: str
    description: str = ""
    client_name: str
    jurisdiction: str = ""


class MatterResponse(BaseModel):
    """Matter response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    client_name: str
    jurisdiction: str
    is_active: bool


class MatterDetailResponse(MatterResponse):
    """Detailed matter response with members."""

    members: list[dict[str, str]] = []


class MatterMemberRequest(BaseModel):
    """Request to add member to matter."""

    user_id: str


@router.get("", response_model=list[MatterResponse])
async def list_matters(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MatterResponse]:
    """List matters accessible to current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of matters user has access to
    """
    query = select(Matter).join(MatterMembership).where(MatterMembership.user_id == current_user.id)
    result = await db.execute(query)
    matters = result.scalars().all()

    return [
        MatterResponse(
            id=m.id,
            name=m.name,
            description=m.description,
            client_name=m.client_name,
            jurisdiction=m.jurisdiction,
            is_active=m.is_active,
        )
        for m in matters
    ]


@router.post("", response_model=MatterResponse, status_code=status.HTTP_201_CREATED)
async def create_matter(
    matter_data: MatterCreate,
    current_user: Annotated[User, Depends(require_partner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatterResponse:
    """Create a new matter (partner only).

    Args:
        matter_data: Matter creation data
        current_user: Current authenticated partner user
        db: Database session

    Returns:
        Created matter
    """
    matter_id = str(uuid.uuid4())
    matter = Matter(
        id=matter_id,
        name=matter_data.name,
        description=matter_data.description,
        client_name=matter_data.client_name,
        jurisdiction=matter_data.jurisdiction,
    )

    membership = MatterMembership(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        matter_id=matter_id,
        granted_by=current_user.id,
    )

    db.add(matter)
    db.add(membership)
    await db.commit()
    await db.refresh(matter)

    logger.info(f"Matter created: {matter.name} by {current_user.email}")

    return MatterResponse(
        id=matter.id,
        name=matter.name,
        description=matter.description,
        client_name=matter.client_name,
        jurisdiction=matter.jurisdiction,
        is_active=matter.is_active,
    )


@router.get("/{matter_id}", response_model=MatterDetailResponse)
async def get_matter(
    matter_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatterDetailResponse:
    """Get matter details.

    Args:
        matter_id: Matter ID
        current_user: Current authenticated user
        _: Matter access verification
        db: Database session

    Returns:
        Matter details with members
    """
    query = select(Matter).where(Matter.id == matter_id)
    result = await db.execute(query)
    matter = result.scalar_one_or_none()

    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")

    members_query = (
        select(User).join(MatterMembership).where(MatterMembership.matter_id == matter_id)
    )
    members_result = await db.execute(members_query)
    members = members_result.scalars().all()

    return MatterDetailResponse(
        id=matter.id,
        name=matter.name,
        description=matter.description,
        client_name=matter.client_name,
        jurisdiction=matter.jurisdiction,
        is_active=matter.is_active,
        members=[{"id": m.id, "email": m.email, "full_name": m.full_name} for m in members],
    )


@router.post("/{matter_id}/members", status_code=status.HTTP_201_CREATED)
async def add_matter_member(
    matter_id: str,
    member_request: MatterMemberRequest,
    current_user: Annotated[User, Depends(require_partner)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Add user to matter (partner only).

    Args:
        matter_id: Matter ID
        member_request: User to add
        current_user: Current authenticated partner user
        _: Matter access verification
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If user/matter not found or user is already a member
    """
    user_query = select(User).where(User.id == member_request.user_id)
    user_result = await db.execute(user_query)
    target_user = user_result.scalar_one_or_none()

    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await db.execute(
        select(MatterMembership).where(
            and_(
                MatterMembership.user_id == member_request.user_id,
                MatterMembership.matter_id == matter_id,
            )
        )
    )

    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this matter",
        )

    membership = MatterMembership(
        id=str(uuid.uuid4()),
        user_id=member_request.user_id,
        matter_id=matter_id,
        granted_by=current_user.id,
    )

    db.add(membership)
    await db.commit()

    logger.info(f"User {target_user.email} added to matter {matter_id}")

    return {"message": "User added to matter successfully"}


@router.delete("/{matter_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_matter_member(
    matter_id: str,
    user_id: str,
    current_user: Annotated[User, Depends(require_partner)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Remove a user from a matter (partner only).

    The user loses access to all documents and query history within the
    matter. Existing QueryLog rows are retained for audit purposes.

    Args:
        matter_id: Matter ID.
        user_id:   User to remove.

    Returns:
        Success message.

    Raises:
        HTTPException: 400 if trying to remove the last member, 404 if
                       the membership doesn't exist.
    """
    membership_result = await db.execute(
        select(MatterMembership).where(
            and_(
                MatterMembership.user_id == user_id,
                MatterMembership.matter_id == matter_id,
            )
        )
    )
    membership = membership_result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this matter",
        )

    # Guard: don't allow removing the last member
    count_result = await db.execute(
        select(MatterMembership).where(MatterMembership.matter_id == matter_id)
    )
    if len(count_result.scalars().all()) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last member from a matter",
        )

    await db.delete(membership)
    await db.commit()

    logger.info(f"User {user_id} removed from matter {matter_id} by {current_user.email}")
    return {"message": "User removed from matter"}


@router.delete("/{matter_id}", status_code=status.HTTP_200_OK)
async def delete_matter(
    matter_id: str,
    current_user: Annotated[User, Depends(require_partner)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Permanently delete a matter and all associated data (partner only).

    Cascades through documents (Qdrant vectors included), query logs,
    and memberships before removing the matter row itself.
    """
    from app import services

    matter = await db.get(Matter, matter_id)
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")

    # 1. Delete Qdrant vectors for every document in this matter
    docs_result = await db.execute(select(Document).where(Document.matter_id == matter_id))
    for doc in docs_result.scalars().all():
        try:
            if services.vector_store is not None:
                services.vector_store.delete_document(doc.id)
        except Exception as exc:
            logger.error(f"Failed to purge Qdrant chunks for doc {doc.id}: {exc}", exc_info=True)

    # 2. Cascade-delete dependent rows (SQLite doesn't enforce FK cascades)
    await db.execute(delete(QueryLog).where(QueryLog.matter_id == matter_id))
    await db.execute(delete(Document).where(Document.matter_id == matter_id))
    await db.execute(delete(MatterMembership).where(MatterMembership.matter_id == matter_id))
    await db.delete(matter)
    await db.commit()

    logger.info(f"Matter {matter_id} ({matter.name!r}) deleted by {current_user.email}")
    return {"message": "Matter deleted"}
