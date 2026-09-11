"""CI grep-suite scaffolding (coding-guidelines.md § Module size and
forbidden patterns: "Every grep in this section (API-side and web-side,
six checks total) is a named step in T-016's `ci.yml` job").

T-016 wires this into CI; this task (T-006) only scaffolds the six checks
as a single runnable script that exits non-zero on a hit, plus a unit test
(`tests/unit/test_grep_suite.py`) that runs it against the current tree.

Location note (T-006 interpretation): the task brief allowed either
`app/scripts/grep_suite.py` or `scripts/ci/...`; this picks a third
sibling location, **`api/scripts/grep_suite.py`** — outside the `app/`
package the checks scan, so this file's own regex-pattern string literals
can never trip its own API-side checks, and outside `tests/` since it is
meant to be runnable standalone (`uv run python scripts/grep_suite.py`),
not only via pytest.

**Checks 1-3 are a naming-convention aid, not a hard guarantee (review
finding F4).** They are line-based regexes over source text: a determined
rename can still evade them (e.g. `import datetime as _dt` then calling
`_dt.now()` under a second alias, or wrapping a route registration across
several lines). They catch the common-case violation and the alias-import
*itself* (aliasing `datetime`/`HTTPException` is flagged as suspicious on
its own, whether or not the resulting alias is ever called), which is
enough for a human/CI signal — they are not, and are not meant to be, a
sound static analyzer. **Check 4 (the AST walk) is the actual enforcement
layer** for its concern (raw-SQL/raw-DBAPI bypass of the append-only
guard): it parses real syntax trees and cannot be fooled by a rename in
the way 1-3 can.

The six checks (API-side unless noted):

1. `datetime.now()`/`datetime.utcnow()` outside `app/core/clock.py`
   (coding-guidelines.md § Validation and typing / § Forbidden patterns),
   plus an `import datetime as ...`/`from datetime import datetime as ...`
   alias-import anywhere outside `clock.py` (review finding F4: the direct-
   call regex alone is trivially evaded by aliasing the module first).
2. A `PATCH`/`PUT`/`DELETE` route decorator, or an `add_api_route(...)`
   call whose `methods=[...]` argument names one of those verbs on the
   same source line (CORS is `GET,POST` only; review finding F4 adds the
   `add_api_route` form, the other way FastAPI registers a route).
3. `HTTPException(...)` outside the one exception-handler registration
   (ADR-018 — no second, untranslatable error shape), plus a
   `HTTPException as ...` import alias anywhere outside that file (review
   finding F4).
4. Raw-SQL/raw-DBAPI bypass of the append-only guard
   (`exec_driver_sql`/`.cursor()`/a `text()` literal naming an append-only
   table) — **not duplicated here**: this check calls the existing AST walk
   in `tests/unit/test_no_raw_sql_bypass.py` (T-004) directly, per this
   task's brief ("Do not duplicate T-004's test_no_raw_sql_bypass.py —
   call it from the suite or reference it").
5. Web-side: `dangerouslySetInnerHTML`/`innerHTML =`/`eval(`/
   `new Function(`/inline `style=` (frontend-architecture.md §10). No-ops
   (reports zero violations) while `web/` does not exist yet — the
   frontend milestone has not started.
6. Web-side: a complaint number/citizen name/phone value templated into a
   URL/`history` entry, or a third-party script/font/analytics tag
   (security-architecture.md §5/§7, frontend-architecture.md §10). Same
   no-op note as (5).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
_APP_DIR = _API_DIR / "app"
# `web/src` only — never `web/node_modules`, `web/.next` (build output) or
# `web/out` (static export), all of which are full of third-party/minified
# code that would swamp these checks with false positives.
_WEB_DIR = _API_DIR.parent / "web" / "src"

if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))


def _iter_py_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts]


def _iter_web_source_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    extensions = {".ts", ".tsx", ".js", ".jsx"}
    return [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in extensions and "node_modules" not in p.parts
    ]


_DATETIME_NOW_RE = re.compile(r"\bdatetime\.(now|utcnow)\s*\(")
# F4: catch the alias-import itself, not just a direct `datetime.now()`
# call — `import datetime as dt` then `dt.now()` would otherwise evade the
# regex above entirely.
_DATETIME_ALIAS_IMPORT_RE = re.compile(
    r"^\s*(import\s+datetime\s+as\s+\w+|from\s+datetime\s+import\s+datetime\s+as\s+\w+)\b"
)


def check_datetime_now_outside_clock() -> list[str]:
    """[1] `datetime.now()`/`datetime.utcnow()` (direct call or via an
    alias import) outside `app/core/clock.py`. Naming-convention aid, not
    a hard guarantee (review finding F4) — see module docstring."""
    exempt = _APP_DIR / "core" / "clock.py"
    violations = []
    for path in _iter_py_files(_APP_DIR):
        if path == exempt:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _DATETIME_NOW_RE.search(line):
                violations.append(f"{path}:{lineno}: datetime.now()/utcnow() outside core/clock.py")
            elif _DATETIME_ALIAS_IMPORT_RE.search(line):
                violations.append(f"{path}:{lineno}: datetime import alias outside core/clock.py")
    return violations


_ROUTE_DECORATOR_RE = re.compile(r"@\w+(?:\.\w+)*\.(patch|put|delete)\s*\(")
# F4: `router.add_api_route("/x", handler, methods=["PUT"])` is the other
# way FastAPI registers a route — the decorator regex above never sees it.
# Single-line only (see module docstring's "naming-convention aid" note).
_ADD_API_ROUTE_RE = re.compile(r"add_api_route\(")
_FORBIDDEN_VERB_LITERAL_RE = re.compile(r"[\"'](PATCH|PUT|DELETE)[\"']", re.IGNORECASE)


def check_no_patch_put_delete_routes() -> list[str]:
    """[2] No `PATCH`/`PUT`/`DELETE` route decorator or `add_api_route(...,
    methods=[...])` call anywhere (CORS is `GET,POST` only)."""
    violations = []
    for path in _iter_py_files(_APP_DIR):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = _ROUTE_DECORATOR_RE.search(line)
            if match:
                verb = match.group(1)
                violations.append(f"{path}:{lineno}: @...{verb}(...) route decorator forbidden")
            elif _ADD_API_ROUTE_RE.search(line) and _FORBIDDEN_VERB_LITERAL_RE.search(line):
                violations.append(f"{path}:{lineno}: add_api_route(...) names a forbidden verb")
    return violations


_HTTPEXCEPTION_RE = re.compile(r"\bHTTPException\s*\(")
# F4: `from fastapi import HTTPException as HTTPError` then raising
# `HTTPError(...)` would evade the call-site regex above entirely — flag
# the alias import itself instead of chasing every possible alias name.
_HTTPEXCEPTION_ALIAS_IMPORT_RE = re.compile(r"\bHTTPException\s+as\s+\w+")
# The one future exception-handler registration module (T-008) is exempt.
# Kept as a set so a later task can add its own file here without touching
# the check's logic.
_HTTPEXCEPTION_ALLOWED_FILES = frozenset({_APP_DIR / "api" / "exception_handlers.py"})


def check_httpexception_outside_handler() -> list[str]:
    """[3] `HTTPException(...)` (direct call or via an import alias)
    outside the one exception-handler registration (ADR-018)."""
    violations = []
    for path in _iter_py_files(_APP_DIR):
        if path in _HTTPEXCEPTION_ALLOWED_FILES:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _HTTPEXCEPTION_RE.search(line):
                violations.append(f"{path}:{lineno}: bare HTTPException(...) outside the handler")
            elif _HTTPEXCEPTION_ALIAS_IMPORT_RE.search(line):
                violations.append(
                    f"{path}:{lineno}: HTTPException import alias outside the handler"
                )
    return violations


def check_raw_sql_bypass_of_append_only_guard() -> list[str]:
    """[4] Delegates to `tests/unit/test_no_raw_sql_bypass.py`'s AST walk
    (T-004) — not duplicated here, per this task's brief."""
    from tests.unit.test_no_raw_sql_bypass import _check_file, _iter_app_source_files

    violations = []
    for path in _iter_app_source_files():
        violations.extend(_check_file(path))
    return violations


_WEB_DOM_RE = re.compile(
    r"dangerouslySetInnerHTML|innerHTML\s*=|eval\s*\(|new Function\s*\(|style=[\"{]"
)


def check_web_dangerous_dom_patterns() -> list[str]:
    """[5] Web-side: dangerouslySetInnerHTML/innerHTML/eval/new Function/
    inline style (frontend-architecture.md §10). No-ops if `web/` does not
    exist yet."""
    violations = []
    for path in _iter_web_source_files(_WEB_DIR):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _WEB_DOM_RE.search(line):
                violations.append(f"{path}:{lineno}: forbidden DOM/eval pattern")
    return violations


_WEB_PII_URL_RE = re.compile(
    r"(complaint_number|citizen_name|citizen_phone)\b.*(href|router\.push|history\.(push|replace)State|`/)"
)
_WEB_THIRD_PARTY_RE = re.compile(
    r"<script[^>]+src=[\"']https?://|fonts\.googleapis\.com|google-analytics\.com"
)


def check_web_pii_in_url_or_third_party() -> list[str]:
    """[6] Web-side: a complaint number/citizen name/phone value templated
    into a URL/`history` entry, or a third-party script/font/analytics tag
    (security-architecture.md §5/§7). No-ops if `web/` does not exist yet."""
    violations = []
    for path in _iter_web_source_files(_WEB_DIR):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _WEB_PII_URL_RE.search(line) or _WEB_THIRD_PARTY_RE.search(line):
                violations.append(f"{path}:{lineno}: PII-in-URL or third-party-script pattern")
    return violations


_ALL_CHECKS = (
    check_datetime_now_outside_clock,
    check_no_patch_put_delete_routes,
    check_httpexception_outside_handler,
    check_raw_sql_bypass_of_append_only_guard,
    check_web_dangerous_dom_patterns,
    check_web_pii_in_url_or_third_party,
)


def run_all_checks() -> list[str]:
    """Run all six checks; return the combined list of violations (empty =
    clean)."""
    violations: list[str] = []
    for check in _ALL_CHECKS:
        violations.extend(check())
    return violations


def main() -> int:
    violations = run_all_checks()
    if violations:
        print(f"grep_suite: {len(violations)} forbidden-pattern violation(s):", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        return 1
    print("grep_suite: clean (6/6 checks passed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
