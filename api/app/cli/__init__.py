"""Operator CLI entry points (backend-architecture.md §12).

Reachable only via `fly ssh console`, never over HTTP: a layering test
(`tests/unit/test_layering.py`) and a T-007-added test both assert that no
module under `app/api/` or `app/middleware/` imports `app.cli`.
"""

from __future__ import annotations
