"""ADR-007 middleware chain (backend-architecture.md §2). Middleware may
call `services` but must not know about complaints or accounts as domain
concepts — only "is this request allowed" (coding-guidelines.md §
Layering)."""

from __future__ import annotations
