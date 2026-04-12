from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.models import User
from app.db.session import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        token_data = verify_token(token)
    except Exception as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    from sqlalchemy import select

    user_query = select(User).where(User.id == token_data.user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user (not disabled).

    Args:
        current_user: Current authenticated user

    Returns:
        Active user object

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return current_user


async def require_partner(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Dependency that enforces partner-only access.

    Use this on any endpoint that should be restricted to partners,
    e.g. user management, matter creation, and member administration.

    Returns:
        The current user if they are a partner.

    Raises:
        HTTPException: 403 if the user is not a partner.
    """
    from app.db.models import UserRole

    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires partner role",
        )
    return current_user


async def check_matter_access(
    matter_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Check if current user has access to a matter.

    Args:
        matter_id: Matter ID to check access for
        current_user: Current authenticated user
        db: Database session

    Returns:
        Matter ID if access is granted

    Raises:
        HTTPException: If user does not have access to matter
    """
    from sqlalchemy import and_, select

    from app.db.models import MatterMembership

    query = select(MatterMembership).where(
        and_(
            MatterMembership.user_id == current_user.id,
            MatterMembership.matter_id == matter_id,
        )
    )

    result = await db.execute(query)
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this matter",
        )

    return matter_id
