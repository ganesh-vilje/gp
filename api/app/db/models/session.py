"""`session` — mirrors migrations/versions/0001_initial.py 1:1."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class Session(Base):
    __tablename__ = "session"
    __table_args__ = (
        sa.UniqueConstraint("token_hash", name="uq_session_token_hash"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["clerk_account.id"],
            name="fk_session_user_id_clerk_account",
            ondelete="CASCADE",
        ),
        sa.Index("ix_session_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger(), primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    token_hash: Mapped[str] = mapped_column(sa.CHAR(length=64), nullable=False)
    csrf_token: Mapped[str] = mapped_column(sa.CHAR(length=64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    absolute_expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
