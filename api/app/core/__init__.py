"""Pure, side-effect-free core modules (backend-architecture.md §1).

`core` owns settings-independent building blocks — the error taxonomy,
complaint-number codec, validation rules, hashing wrappers, the injectable
clock, and the single user-visible-strings module (AD-12). Nothing in
`core` imports `app.db`, `app.services`, `app.api`, `app.middleware`, or
`app.cli` (coding-guidelines.md § Layering) — asserted by
`tests/unit/test_layering.py`.
"""

from __future__ import annotations
