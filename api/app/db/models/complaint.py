"""`complaint` — mirrors migrations/versions/0001_initial.py 1:1."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models._enums import complaint_status_enum
from app.db.models.base import Base


class Complaint(Base):
    __tablename__ = "complaint"
    __table_args__ = (
        sa.UniqueConstraint("complaint_number", name="uq_complaint_number"),
        sa.UniqueConstraint("client_request_id", name="uq_complaint_client_request_id"),
        sa.CheckConstraint(
            "complaint_number ~ '^[0-9A-HJKMNP-TV-Z]{9}$'",
            name="ck_complaint_number_format",
        ),
        sa.CheckConstraint(
            "length(trim(citizen_name)) > 0", name="ck_complaint_citizen_name_not_blank"
        ),
        sa.CheckConstraint(
            r"citizen_phone ~ '^\+?[0-9]{7,15}$'", name="ck_complaint_citizen_phone_format"
        ),
        sa.CheckConstraint(
            "length(trim(description)) > 0", name="ck_complaint_description_not_blank"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["clerk_account.id"],
            name="fk_complaint_created_by_clerk_account",
            ondelete="RESTRICT",
        ),
        sa.Index(
            "ix_complaint_status_created_id",
            "status",
            sa.text("created_at DESC"),
            sa.text("id DESC"),
        ),
        sa.Index("ix_complaint_created_id", sa.text("created_at DESC"), sa.text("id DESC")),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger(), primary_key=True)
    complaint_number: Mapped[str] = mapped_column(sa.CHAR(length=9), nullable=False)
    client_request_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)
    citizen_name: Mapped[str] = mapped_column(sa.String(length=100), nullable=False)
    citizen_phone: Mapped[str] = mapped_column(sa.String(length=16), nullable=False)
    description: Mapped[str] = mapped_column(sa.String(length=2000), nullable=False)
    status: Mapped[str] = mapped_column(complaint_status_enum, nullable=False, server_default="new")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    created_by: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
