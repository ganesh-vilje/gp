"""`rate_limit_counter` — mirrors migrations/versions/0001_initial.py 1:1.

Written exclusively via the limiter's dedicated AUTOCOMMIT engine
(backend-architecture.md §5/§10) — this module only declares the shape.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class RateLimitCounter(Base):
    __tablename__ = "rate_limit_counter"
    __table_args__ = (
        sa.PrimaryKeyConstraint("scope", "key", "window_start", name="pk_rate_limit_counter"),
        sa.Index("ix_rate_limit_counter_window_start", "window_start"),
    )

    scope: Mapped[str] = mapped_column(sa.String(length=20), nullable=False)
    key: Mapped[str] = mapped_column(sa.String(length=80), nullable=False)
    window_start: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(sa.Integer(), nullable=False, server_default=sa.text("1"))
