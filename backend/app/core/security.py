from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


class TokenData(BaseModel):
    """JWT token payload."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    role: str
    matter_ids: list[str] = []


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create JWT access token.

    Args:
        data: Token claims
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create JWT refresh token.

    Args:
        data: Token claims

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> TokenData:
    """Verify and decode JWT token.

    Access tokens carry no ``type`` claim (defaults to ``"access"``);
    refresh tokens are minted with ``type: "refresh"`` by
    :func:`create_refresh_token`. Passing the wrong token type — e.g. a
    refresh token to an endpoint expecting an access token — fails
    verification, so the two cannot be used interchangeably.

    Args:
        token: JWT token to verify
        expected_type: Either "access" or "refresh"

    Returns:
        TokenData with claims

    Raises:
        JWTError: If token is invalid, expired, or the wrong type
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        token_type = payload.get("type", "access")
        if token_type != expected_type:
            raise JWTError(f"Expected a {expected_type} token, got {token_type}")

        user_id: str | None = payload.get("user_id")
        email: str | None = payload.get("email")
        role: str | None = payload.get("role")

        if user_id is None or email is None or role is None:
            raise JWTError("Invalid token claims")

        token_data = TokenData(
            user_id=user_id,
            email=email,
            role=role,
            matter_ids=payload.get("matter_ids", []),
        )
        return token_data
    except JWTError as e:
        raise JWTError(f"Could not validate credentials: {str(e)}")


def get_password_hash(password: str) -> str:
    """Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
