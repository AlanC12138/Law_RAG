from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models import User, UserRole

logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Create all database tables if they do not exist.

    In development this replaces running ``alembic upgrade head`` manually.
    In production, prefer Alembic so migrations are tracked and reversible.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    logger.info("Database tables verified / created")


async def seed_admin(db: AsyncSession) -> None:
    """Create a default partner admin account if no users exist.

    Credentials are read from environment variables so they can be
    changed without touching code. The seed only runs once — if any
    user already exists the function is a no-op.

    Env vars:
        ADMIN_EMAIL    (default: admin@lawfirm.local)
        ADMIN_PASSWORD (default: changeme — MUST be changed in production)
        ADMIN_NAME     (default: Admin Partner)
    """
    settings = get_settings()

    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # users already exist — skip seeding

    admin = User(
        id=str(uuid.uuid4()),
        email=settings.admin_email,
        hashed_password=get_password_hash(settings.admin_password),
        full_name=settings.admin_name,
        role=UserRole.PARTNER,
        is_active=True,
    )
    db.add(admin)
    await db.commit()

    logger.warning(
        f"Seeded default admin user: {settings.admin_email} — "
        "change the password immediately via ADMIN_PASSWORD env var"
    )
