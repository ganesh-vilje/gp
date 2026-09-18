"""Runs `scripts/grep_suite.py`'s six forbidden-pattern checks against the
current tree (T-006 scaffolding; T-016 wires the script itself into CI),
plus one negative case per alias-import/route pattern added by review
finding F4 — each writes a throwaway `.py` file under `app/` (checks 1-3
hardcode `app/` as their scan root, so a real file under it is the only
way to exercise them) and always removes it, even on failure.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import grep_suite  # noqa: E402

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "grep_suite.py"
_APP_DIR = _SCRIPT_PATH.parents[1] / "app"


def test_run_all_checks_finds_no_violations_in_the_current_tree() -> None:
    assert grep_suite.run_all_checks() == []


def test_script_is_runnable_and_exits_zero_when_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(_SCRIPT_PATH.parents[1]),
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "clean" in result.stdout


@pytest.fixture
def temp_app_file() -> Iterator[Path]:
    """A throwaway module under `app/`, always removed afterward."""
    path = _APP_DIR / "_grep_suite_review_fixture_tmp.py"
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def test_check_1_flags_a_datetime_alias_import(temp_app_file: Path) -> None:
    """F4: `import datetime as dt` is flagged even with no direct
    `datetime.now()`/`datetime.utcnow()` call in the file."""
    temp_app_file.write_text("import datetime as dt\n", encoding="utf-8")

    violations = grep_suite.check_datetime_now_outside_clock()

    assert any(temp_app_file.name in v for v in violations)


def test_check_2_flags_add_api_route_with_a_forbidden_verb(temp_app_file: Path) -> None:
    """F4: `add_api_route(..., methods=["PUT"])` is the other way FastAPI
    registers a route; the decorator-only regex never saw this form."""
    temp_app_file.write_text(
        'router.add_api_route("/x", handler, methods=["PUT"])\n', encoding="utf-8"
    )

    violations = grep_suite.check_no_patch_put_delete_routes()

    assert any(temp_app_file.name in v for v in violations)


def test_check_3_flags_an_httpexception_import_alias(temp_app_file: Path) -> None:
    """F4: `from fastapi import HTTPException as HTTPError` is flagged even
    with no direct `HTTPException(...)` call spelled out in the file."""
    temp_app_file.write_text("from fastapi import HTTPException as HTTPError\n", encoding="utf-8")

    violations = grep_suite.check_httpexception_outside_handler()

    assert any(temp_app_file.name in v for v in violations)
