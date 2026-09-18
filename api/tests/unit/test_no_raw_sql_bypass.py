"""AST guard against raw-SQL/raw-DBAPI bypasses of app/db/guard.py
(T-004 rework, code-reviewer F1).

The runtime `before_execute` guard (app/db/guard.py) catches every
Core/ORM-compiled statement, including `text()` constructs — but it
cannot see `Connection.exec_driver_sql()` or a raw DBAPI `.cursor()`,
because both skip SQLAlchemy's Core execute-event pipeline entirely. This
is therefore a static check, not a runtime one: nothing under `app/` may
call `exec_driver_sql`, obtain/call a raw `.cursor()`, or author a
`text()` literal that mentions one of the three append-only table names
(coding-guidelines.md § Forbidden patterns: "do not write code that relies
on being caught — do not write it at all"). Mirrored by a grep in T-016's
CI job.
"""

from __future__ import annotations

import ast
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[2] / "app"

_APPEND_ONLY_TABLES = ("complaint_status_history", "complaint_edit_history", "security_event")


def _iter_app_source_files() -> list[Path]:
    return [p for p in sorted(_APP_ROOT.rglob("*.py")) if "__pycache__" not in p.parts]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _check_file(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "exec_driver_sql":
            violations.append(f"{path}: exec_driver_sql(...) call bypasses the append-only guard")
        elif name == "cursor":
            violations.append(f"{path}: raw DBAPI .cursor(...) call bypasses the append-only guard")
        elif name == "text" and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                literal = first_arg.value.lower()
                for table in _APPEND_ONLY_TABLES:
                    if table in literal:
                        violations.append(
                            f"{path}: text(...) literal mentions append-only table {table!r}"
                        )
    return violations


def test_no_raw_sql_bypass_of_append_only_guard() -> None:
    violations: list[str] = []
    for path in _iter_app_source_files():
        violations.extend(_check_file(path))
    assert not violations, "Raw-SQL bypass risk(s) found:\n" + "\n".join(violations)
