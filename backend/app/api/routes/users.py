from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, require_partner
from app.core.security import get_password_hash
from app.db.models import User, UserRole
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Payload for creating a new user account."""

    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.ASSOCIATE


class UserResponse(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class UserUpdate(BaseModel):
    """Partial update payload — all fields optional."""

    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[UserResponse])
async def list_users(
    _: Annotated[User, Depends(require_partner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserResponse]:
    """List all firm users. Partner-only.

    Returns:
        All user accounts ordered by creation date.
    """
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [_to_response(u) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: Annotated[User, Depends(require_partner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Create a new user account. Partner-only.

    Args:
        payload: New user details including plain-text password.

    Returns:
        Created user.

    Raises:
        HTTPException: 409 if email already registered.
    """
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email already registered: {payload.email}",
        )

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User created: {user.email} ({user.role}) by partner")
    return _to_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return _to_response(current_user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: Annotated[User, Depends(require_partner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Update a user's profile or role. Partner-only.

    Args:
        user_id: Target user UUID.
        payload: Fields to update (all optional).

    Returns:
        Updated user.

    Raises:
        HTTPException: 404 if user not found, 400 if trying to demote the
                       last active partner.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Guard: don't allow removing the last active partner
    if payload.role is not None and payload.role != UserRole.PARTNER:
        if user.role == UserRole.PARTNER:
            await _assert_not_last_partner(db, user_id)

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        if not payload.is_active and user.role == UserRole.PARTNER:
            await _assert_not_last_partner(db, user_id)
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)

    logger.info(f"User updated: {user.email} by {current_user.email}")
    return _to_response(user)


@router.delete("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str,
    current_user: Annotated[User, Depends(require_partner)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Deactivate a user account (soft delete). Partner-only.

    Deactivated users cannot log in but their query history is preserved.

    Args:
        user_id: Target user UUID.

    Returns:
        Deactivated user.

    Raises:
        HTTPException: 400 if trying to deactivate the last active partner
                       or deactivating yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.PARTNER:
        await _assert_not_last_partner(db, user_id)

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    logger.info(f"User deactivated: {user.email} by {current_user.email}")
    return _to_response(user)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


async def _assert_not_last_partner(db: AsyncSession, exclude_user_id: str) -> None:
    """Raise 400 if the given user is the last active partner."""
    result = await db.execute(
        select(User).where(
            User.role == UserRole.PARTNER,
            User.is_active == True,  # noqa: E712
            User.id != exclude_user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote or deactivate the last active partner",
        )
