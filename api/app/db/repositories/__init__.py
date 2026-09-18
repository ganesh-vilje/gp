"""Thin query/persist functions over `app.db.models` (backend-architecture.md
§1). Never enforce a business rule or decide a status transition — that is
`app/services/`'s job (coding-guidelines.md § Layering)."""

from __future__ import annotations
