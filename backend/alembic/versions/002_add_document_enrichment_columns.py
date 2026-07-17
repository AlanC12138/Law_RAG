"""Add document enrichment columns — summary, clauses_json.

Revision ID: 002
Revises: 001
Create Date: 2026-07-16

These columns back the LLM summarisation and clause-extraction features
added in v0.2.0. They were previously added ad hoc via raw ALTER TABLE
statements in app/db/init_db.py (SQLite only); this migration is the
authoritative, database-agnostic version of that same change.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("summary", sa.String(2000), nullable=True))
    op.add_column("documents", sa.Column("clauses_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "clauses_json")
    op.drop_column("documents", "summary")
