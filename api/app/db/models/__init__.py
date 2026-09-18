"""SQLAlchemy 2.x ORM models — one module per table, mirroring
migrations/versions/0001_initial.py 1:1 (T-004).

`Base` is re-exported here for `migrations/env.py`'s
`target_metadata = Base.metadata`. Every model module is imported so its
table is registered on `Base.metadata` before that happens.
"""

from __future__ import annotations

from app.db.models.base import Base
from app.db.models.clerk_account import ClerkAccount
from app.db.models.complaint import Complaint
from app.db.models.complaint_edit_history import ComplaintEditHistory
from app.db.models.complaint_status_history import ComplaintStatusHistory
from app.db.models.rate_limit_counter import RateLimitCounter
from app.db.models.security_event import SecurityEvent
from app.db.models.session import Session

__all__ = [
    "Base",
    "ClerkAccount",
    "Complaint",
    "ComplaintEditHistory",
    "ComplaintStatusHistory",
    "RateLimitCounter",
    "SecurityEvent",
    "Session",
]
