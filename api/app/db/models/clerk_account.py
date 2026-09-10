"""`clerk_account` — mirrors migrations/versions/0001_initial.py 1:1."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ClerkAccount(Base):
    __tablename__ = "clerk_account"
    __table_args__ = (
        sa.UniqueConstraint("username", name="uq_clerk_account_username"),
        sa.CheckConstraint(
            r"username ~ '^[A-Za-z0-9_]{3,30}$'", name="ck_clerk_account_username_format"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["clerk_account.id"],
            name="fk_clerk_account_created_by_clerk_account",
            ondelete="SET NULL",
        ),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger(), primary_key=True)
    username: Mapped[str] = mapped_column(sa.String(length=30), nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    is_admin_clerk: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.text("false")
    )
    must_change_password: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.text("true")
    )
    password_is_otp: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.text("false")
    )
    password_set_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger(), nullable=True)
