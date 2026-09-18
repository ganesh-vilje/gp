"""Request/response DTOs for the API layer (backend-architecture.md §1).

Every DTO here is a pydantic model with `extra="forbid"` — a request DTO
rejects an unexpected field as `422`; a response DTO is exhaustive, never
"returns the object" (coding-guidelines.md § Validation and typing,
api-contract.md § Conventions "response_model discipline").
"""

from __future__ import annotations
