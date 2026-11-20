"""Make timestamp columns timezone-aware.

Revision ID: 003
Revises: 002
Create Date: 2026-07-17

Every model in db/models.py stamps timestamps with
``datetime.now(timezone.utc)`` — a timezone-*aware* value. Migration 001
declared these columns as plain ``sa.DateTime()``, which Postgres creates
as ``TIMESTAMP WITHOUT TIME ZONE``. SQLite never enforced this distinction
(it just stores whatever string you hand it), so the mismatch was
invisible there — but asyncpg rejects inserting an aware datetime into a
naive-typed column outright: "can't subtract offset-naive and
offset-aware datetimes". This surfaced immediately on the very first
insert (seeding the admin user) against a real Postgres database.

Existing values are unambiguously UTC (that's all this app has ever
written), so the conversion interprets them as UTC rather than the
session's local timezone setting.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

_COLUMNS = [
    ("users", "created_at"),
    ("matters", "created_at"),
    ("matter_memberships", "granted_at"),
    ("documents", "created_at"),
    ("documents", "ingested_at"),
    ("query_logs", "created_at"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
