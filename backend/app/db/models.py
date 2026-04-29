from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, PyEnum):
    """User role enumeration."""

    PARTNER = "partner"
    ASSOCIATE = "associate"
    PARALEGAL = "paralegal"


class DocumentStatus(str, PyEnum):
    """Document processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.ASSOCIATE)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=func.now()
    )

    matters: Mapped[list[Matter]] = relationship(
        secondary="matter_memberships",
        back_populates="members",
        lazy="selectin",
    )
    query_logs: Mapped[list[QueryLog]] = relationship(back_populates="user", lazy="selectin")


class Matter(Base):
    """Legal matter/case model."""

    __tablename__ = "matters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(String(1000), default="")
    client_name: Mapped[str] = mapped_column(String(255))
    jurisdiction: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=func.now()
    )

    documents: Mapped[list[Document]] = relationship(back_populates="matter", lazy="selectin")
    members: Mapped[list[User]] = relationship(
        secondary="matter_memberships",
        back_populates="matters",
        lazy="selectin",
    )
    query_logs: Mapped[list[QueryLog]] = relationship(back_populates="matter", lazy="selectin")


class MatterMembership(Base):
    """Association between users and matters."""

    __tablename__ = "matter_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), index=True)
    granted_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=func.now()
    )
    granted_by: Mapped[str] = mapped_column(String(36), default="")


class Document(Base):
    """Uploaded legal document model."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), index=True)
    filename: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(50))
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING
    )
    page_count: Mapped[int] = mapped_column(default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(String(2000), nullable=True, default=None)
    ingested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=func.now()
    )

    matter: Mapped[Matter] = relationship(back_populates="documents")


class QueryLog(Base):
    """Log of user queries and LLM responses."""

    __tablename__ = "query_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), index=True)
    query_text: Mapped[str] = mapped_column(String(1000))
    answer_text: Mapped[str] = mapped_column(String(4000))
    source_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="query_logs")
    matter: Mapped[Matter] = relationship(back_populates="query_logs")
