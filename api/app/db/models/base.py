"""Shared declarative base for every ORM model (SQLAlchemy 2.x `Mapped[...]`).

A single `Base` so `Base.metadata` (imported by `migrations/env.py`) sees
every table for `alembic check` to diff against.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by every table module in this package."""
