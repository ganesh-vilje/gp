"""`complaint_edit_history` — append-only (BR-008); mirrors 0001_initial.py 1:1."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ComplaintEditHistory(Base):
    __tablename__ = "complaint_edit_history"
    __table_args__ = (
        sa.CheckConstraint(
            "field_name IN ('citizen_name','citizen_phone','description')",
            name="ck_complaint_edit_history_field_name_allowed",
        ),
        sa.CheckConstraint(
            "new_value IS DISTINCT FROM previous_value",
            name="ck_complaint_edit_history_value_changed",
        ),
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaint.id"],
            name="fk_complaint_edit_history_complaint_id_complaint",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["clerk_account.id"],
            name="fk_complaint_edit_history_actor_id_clerk_account",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_ceh_complaint_created", "complaint_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger(), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    field_name: Mapped[str] = mapped_column(sa.String(length=20), nullable=False)
    previous_value: Mapped[str] = mapped_column(sa.String(length=2000), nullable=False)
    new_value: Mapped[str] = mapped_column(sa.String(length=2000), nullable=False)
    actor_id: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
