from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Matter, MatterMembership, User, UserRole
from app.db.session import get_db
from app.main import app
from app.core.security import get_password_hash


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create in-memory SQLite test database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create test user."""
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        role=UserRole.ASSOCIATE,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_matter(test_db: AsyncSession, test_user: User) -> Matter:
    """Create test matter with user membership."""
    matter_id = str(uuid.uuid4())
    matter = Matter(
        id=matter_id,
        name="Test Matter",
        description="Test matter for unit testing",
        client_name="Test Client",
        jurisdiction="Federal",
        is_active=True,
    )

    membership = MatterMembership(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        matter_id=matter_id,
        granted_by=test_user.id,
    )

    test_db.add(matter)
    test_db.add(membership)
    await test_db.commit()
    await test_db.refresh(matter)
    return matter


@pytest.fixture
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with test database."""

    def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
