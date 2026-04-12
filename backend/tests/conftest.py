from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.models import Matter, MatterMembership, User, UserRole
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# In-memory SQLite engine shared across a test session
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
_TestSessionLocal = sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Create all tables once per test session."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional test session that is rolled back after each test
    so tests are fully isolated.
    """
    async with _engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ---------------------------------------------------------------------------
# Helper: create users / matters in a session
# ---------------------------------------------------------------------------

async def make_user(
    db: AsyncSession,
    *,
    email: str = "user@example.com",
    password: str = "password123",
    full_name: str = "Test User",
    role: UserRole = UserRole.ASSOCIATE,
    is_active: bool = True,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def make_matter(
    db: AsyncSession,
    *,
    owner: User,
    name: str = "Test Matter",
    client_name: str = "Test Client",
) -> Matter:
    matter_id = str(uuid.uuid4())
    matter = Matter(
        id=matter_id,
        name=name,
        description="A test matter",
        client_name=client_name,
        jurisdiction="Federal",
        is_active=True,
    )
    membership = MatterMembership(
        id=str(uuid.uuid4()),
        user_id=owner.id,
        matter_id=matter_id,
        granted_by=owner.id,
    )
    db.add(matter)
    db.add(membership)
    await db.commit()
    await db.refresh(matter)
    return matter


def auth_headers(user: User) -> dict[str, str]:
    """Return Authorization headers with a fresh token for *user*."""
    token = create_access_token(
        data={"user_id": user.id, "email": user.email, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def partner(test_db: AsyncSession) -> User:
    return await make_user(
        test_db,
        email="partner@firm.com",
        role=UserRole.PARTNER,
        full_name="Lead Partner",
    )


@pytest_asyncio.fixture()
async def associate(test_db: AsyncSession) -> User:
    return await make_user(
        test_db,
        email="associate@firm.com",
        role=UserRole.ASSOCIATE,
        full_name="Junior Associate",
    )


@pytest_asyncio.fixture()
async def matter(test_db: AsyncSession, partner: User) -> Matter:
    return await make_matter(test_db, owner=partner)


@pytest_asyncio.fixture()
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client wired to the test database.

    ``get_db`` is overridden to return our transactional test session so every
    request participates in the same transaction (which is rolled back after
    the test).
    """

    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
