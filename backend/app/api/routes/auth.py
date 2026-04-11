from __future__ import annotations

import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.db.models import User
from app.db.session import get_db
from app.api.dependencies import get_current_active_user
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class TokenResponse(BaseModel):
    """JWT token response."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate user and return JWT tokens.

    Args:
        form_data: Username (email) and password
        db: Database session

    Returns:
        TokenResponse with access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
        },
        expires_delta=access_token_expires,
    )

    refresh_token = create_refresh_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
        }
    )

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, str]:
    """Logout user (invalidate token).

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse with user details
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )
