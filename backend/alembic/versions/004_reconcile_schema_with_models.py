"""Reconcile the schema with the ORM models.

Revision ID: 004
Revises: 003
Create Date: 2026-11-22

`alembic check` (added to CI in this change) reported three differences
between `app/db/models.py` and the schema the migrations actually build.
None of them had broken anything yet, but each is a real divergence:

1. `documents.metadata_json` — the model declares
   ``Mapped[dict[str, Any]]`` with ``default=dict``, i.e. NOT NULL, while
   migration 001 created the column nullable. The ORM would hand back
   ``None`` for a field typed as a dict if anything ever wrote a NULL.
2. `query_logs.source_chunk_ids` — the same mismatch.
3. `users.email` — the model declares ``unique=True, index=True``, which
   SQLAlchemy renders as a single UNIQUE INDEX. Migration 001 instead
   produced a column-level UNIQUE constraint (`users_email_key`) *plus* a
   separate non-unique index of the same name as the intended one. Email
   stayed unique either way, so this was cosmetic — but it made
   autogenerate report drift on every run, which is how a real drift
   would have been missed.

Both columns are backfilled before being tightened so an existing NULL
cannot block the ALTER.

Like 003, this is written for PostgreSQL — the SQLite fallback path builds
its schema with ``Base.metadata.create_all`` and never runs Alembic.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE documents SET metadata_json = '{}' WHERE metadata_json IS NULL")
    op.alter_column(
        "documents",
        "metadata_json",
        existing_type=sa.JSON(),
        nullable=False,
    )

    op.execute("UPDATE query_logs SET source_chunk_ids = '[]' WHERE source_chunk_ids IS NULL")
    op.alter_column(
        "query_logs",
        "source_chunk_ids",
        existing_type=sa.JSON(),
        nullable=False,
    )

    # Replace the constraint + plain index pair with the single unique index
    # the model actually describes. Postgres DDL is transactional, so there
    # is no window where email is unenforced.
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_unique_constraint("users_email_key", "users", ["email"])

    op.alter_column(
        "query_logs",
        "source_chunk_ids",
        existing_type=sa.JSON(),
        nullable=True,
    )
    op.alter_column(
        "documents",
        "metadata_json",
        existing_type=sa.JSON(),
        nullable=True,
    )
