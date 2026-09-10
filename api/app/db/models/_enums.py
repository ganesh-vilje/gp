"""Shared Postgres enum types (mirrors migrations/versions/0001_initial.py).

`create_type=False` on both: the migration creates the Postgres `TYPE`
objects explicitly (`upgrade()`); models only ever reference the existing
type by name so `alembic check` never proposes creating (or re-creating) it.
One module-level instance per enum is imported by every column that uses
it, so SQLAlchemy treats every reference as the same type object.
"""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

COMPLAINT_STATUS_VALUES = ("new", "in_progress", "resolved", "rejected", "closed")
SECURITY_EVENT_TYPE_VALUES = (
    "login_success",
    "login_failure",
    "account_created",
    "password_reset_issued",
    "throttle_lookup",
    "throttle_login",
    "throttle_detail",
    "throttle_write",
    "throttle_search",
    "account_unlocked",
)

complaint_status_enum = postgresql.ENUM(
    *COMPLAINT_STATUS_VALUES, name="complaint_status", create_type=False
)
security_event_type_enum = postgresql.ENUM(
    *SECURITY_EVENT_TYPE_VALUES, name="security_event_type", create_type=False
)
