from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models import User, UserRole

logger = logging.getLogger(__name__)

# backend/ — where alembic.ini and alembic/ live. Three parents up from
# this file: app/db/init_db.py -> app/db -> app -> backend/.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


async def create_tables() -> None:
    """Bring the database schema up to date.

    Postgres (the default when running via docker-compose) is migrated
    with real, version-tracked Alembic revisions — the authoritative path.
    SQLite (the lightweight fallback for running the API without Docker,
    and what the test suite uses) keeps the original create_all + ad hoc
    column patcher, since introducing Alembic's version tracking there
    would be a needless complication for a throwaway dev database.
    """
    settings = get_settings()
    if settings.database_url.startswith("postgresql"):
        await _run_alembic_upgrade()
    else:
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _migrate_columns(conn)
        await engine.dispose()
    logger.info("Database tables verified / created")


async def _run_alembic_upgrade() -> None:
    """Run ``alembic upgrade head`` as a subprocess against Postgres.

    Alembic's Config/command API isn't safely callable from within a
    running asyncio event loop — env.py itself calls ``asyncio.run()``
    internally to support the async engine, and asyncio.run() cannot be
    nested inside an already-running loop (which this function's caller,
    the FastAPI lifespan, is). Shelling out avoids that entirely and is
    otherwise identical to running ``alembic upgrade head`` by hand.
    """
    proc = await asyncio.create_subprocess_exec(
        "alembic",
        "upgrade",
        "head",
        cwd=str(_BACKEND_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output, _ = await proc.communicate()
    decoded = output.decode(errors="replace").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"alembic upgrade head failed (exit {proc.returncode}):\n{decoded}")
    logger.info(f"Alembic migrations applied:\n{decoded}")


async def _migrate_columns(conn) -> None:
    """Add new columns to existing tables without dropping data.

    SQLite does not support IF NOT EXISTS on ALTER TABLE, so we attempt
    each ALTER and silently ignore the error if the column already exists.
    New columns added here must also be declared in db/models.py.
    """
    new_columns = [
        "ALTER TABLE documents ADD COLUMN summary VARCHAR(2000)",
        "ALTER TABLE documents ADD COLUMN clauses_json TEXT",
    ]
    for stmt in new_columns:
        try:
            await conn.execute(text(stmt))
            logger.info(f"Migration applied: {stmt}")
        except OperationalError as exc:
            # "duplicate column name" is the expected error when the column
            # already exists — anything else is worth knowing about.
            if "duplicate column" in str(exc).lower():
                logger.debug(f"Column already exists, skipping: {stmt}")
            else:
                logger.warning(f"Migration skipped due to unexpected error ({stmt}): {exc}")


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
