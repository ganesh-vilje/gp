"""`security_event` — append-only (BR-008); mirrors 0001_initial.py 1:1."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models._enums import security_event_type_enum
from app.db.models.base import Base


class SecurityEvent(Base):
    __tablename__ = "security_event"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["clerk_account.id"],
            name="fk_security_event_actor_user_id_clerk_account",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["clerk_account.id"],
            name="fk_security_event_target_user_id_clerk_account",
            ondelete="SET NULL",
        ),
        sa.Index("ix_security_event_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger(), primary_key=True)
    event_type: Mapped[str] = mapped_column(security_event_type_enum, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(sa.BigInteger(), nullable=True)
    target_user_id: Mapped[int | None] = mapped_column(sa.BigInteger(), nullable=True)
    actor_username_hash: Mapped[str | None] = mapped_column(sa.CHAR(length=16), nullable=True)
    derived_ip: Mapped[str | None] = mapped_column(sa.String(length=45), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(sa.String(length=40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
