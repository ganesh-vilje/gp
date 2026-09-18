"""`complaint_status_history` — append-only (BR-008); mirrors 0001_initial.py 1:1."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models._enums import complaint_status_enum
from app.db.models.base import Base


class ComplaintStatusHistory(Base):
    __tablename__ = "complaint_status_history"
    __table_args__ = (
        sa.CheckConstraint(
            "new_status <> previous_status", name="ck_complaint_status_history_status_changed"
        ),
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaint.id"],
            name="fk_complaint_status_history_complaint_id_complaint",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["clerk_account.id"],
            name="fk_complaint_status_history_actor_id_clerk_account",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_csh_complaint_created", "complaint_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger(), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    previous_status: Mapped[str] = mapped_column(complaint_status_enum, nullable=False)
    new_status: Mapped[str] = mapped_column(complaint_status_enum, nullable=False)
    note: Mapped[str | None] = mapped_column(sa.String(length=2000), nullable=True)
    actor_id: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
