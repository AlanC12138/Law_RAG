"""Initial schema — all tables.

Revision ID: 001
Revises:
Create Date: 2026-04-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("partner", "associate", "paralegal", name="userrole"),
            nullable=False,
            server_default="associate",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "matters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_matters_name", "matters", ["name"])

    op.create_table(
        "matter_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("matter_id", sa.String(36), sa.ForeignKey("matters.id"), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("granted_by", sa.String(36), nullable=False, server_default=""),
    )
    op.create_index("ix_matter_memberships_user_id", "matter_memberships", ["user_id"])
    op.create_index("ix_matter_memberships_matter_id", "matter_memberships", ["matter_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("matter_id", sa.String(36), sa.ForeignKey("matters.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "ready", "failed", name="documentstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_matter_id", "documents", ["matter_id"])

    op.create_table(
        "query_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("matter_id", sa.String(36), sa.ForeignKey("matters.id"), nullable=False),
        sa.Column("query_text", sa.String(1000), nullable=False),
        sa.Column("answer_text", sa.String(4000), nullable=False, server_default=""),
        sa.Column("source_chunk_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_query_logs_user_id", "query_logs", ["user_id"])
    op.create_index("ix_query_logs_matter_id", "query_logs", ["matter_id"])


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_table("documents")
    op.drop_table("matter_memberships")
    op.drop_table("matters")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS documentstatus")
