from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    future=True,
)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Alias used by main.py lifespan and any other code expecting this name
AsyncSessionLocal = async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for dependency injection.

    Yields:
        AsyncSession instance
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
