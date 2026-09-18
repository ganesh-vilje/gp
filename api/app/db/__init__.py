"""Database layer: engines, session dependency, ORM models, append-only guard.

Module layout per backend-architecture.md §1. This package may import
`app.core`; nothing above it (`services`, `api`, `middleware`, `cli`) may be
imported from here (coding-guidelines.md § Layering).
"""

from __future__ import annotations
