"""Import-graph layering test [A-F8] (coding-guidelines.md § Layering, ADR-015).

Walks every `.py` file under `app/` with `ast` and asserts that no module
imports a sibling package "above" it in the dependency direction ADR-015
fixes: `api -> services -> repositories/db -> core`, with everything free
to import `core` (backend-architecture.md §1). This is deliberately a
hand-written AST/import-walk check, not `import-linter` (dependency-
strategy.md — not in the approved dev-dependency list); it must never be
weakened (coding-guidelines.md § Layering).

The rank table below encodes the full dependency direction so this test is
also correct for the packages named in the module layout that do not exist
yet (`app/db`, `app/services`, `app/api`, `app/middleware`, `app/cli`) —
adding one of those packages later needs no change here, only new source
files that respect the table. It also covers, as corollaries, the two
assertions coding-guidelines.md names explicitly: no `services` module
imports `api`, and no `core` module imports `services`.
"""

from __future__ import annotations

import ast
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[2]
_APP_ROOT = _API_DIR / "app"

# Lower rank = closer to the bottom of the dependency direction. A module in
# package X may import `app.<package>` only when that package's rank is <=
# X's own rank (i.e. the same package, or one strictly "below" it).
_PACKAGE_RANK: dict[str, int] = {
    "app.core": 0,
    "app.db": 1,
    "app.services": 2,
    "app.middleware": 3,
    "app.api": 4,
    "app.cli": 4,
}

# The composition root: modules that legitimately wire every layer together
# and are therefore exempt from the rank check (backend-architecture.md §1:
# "main.py # create_app(): settings -> selfcheck -> middleware -> routers").
_COMPOSITION_ROOT_MODULES = {"app", "app.main", "app.settings", "app.selfcheck"}


def _module_name_for(path: Path) -> str:
    rel = path.relative_to(_API_DIR)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else "app"


def _package_of(module_name: str) -> str:
    """Return the `app.<package>` prefix for a module, or "" if top-level."""
    parts = module_name.split(".")
    if len(parts) < 2:
        return ""
    return f"{parts[0]}.{parts[1]}"


def _resolve_relative_import(module_name: str, node: ast.ImportFrom) -> str | None:
    base_parts = module_name.split(".")
    level = node.level
    if level > len(base_parts):
        return None
    base = base_parts[: len(base_parts) - level]
    prefix = ".".join(base)
    if node.module:
        return f"{prefix}.{node.module}" if prefix else node.module
    return prefix or None


def _imported_modules(module_name: str, path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                resolved = _resolve_relative_import(module_name, node)
                if resolved:
                    imported.append(resolved)
            elif node.module:
                imported.append(node.module)
    return imported


def _iter_app_source_files() -> list[tuple[str, Path]]:
    files = []
    for path in sorted(_APP_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        files.append((_module_name_for(path), path))
    return files


def test_layering_no_module_imports_an_upward_package() -> None:
    """[A-F8] Dependencies point downward only: a module may import
    `app.<package>` only when that package's rank is <= its own."""
    violations: list[str] = []

    for module_name, path in _iter_app_source_files():
        if module_name in _COMPOSITION_ROOT_MODULES:
            continue
        importer_package = _package_of(module_name)
        importer_rank = _PACKAGE_RANK.get(importer_package)
        if importer_rank is None:
            continue  # not one of the layered packages this table governs

        for imported in _imported_modules(module_name, path):
            if not imported.startswith("app."):
                continue
            imported_package = _package_of(imported)
            if imported_package == importer_package:
                continue
            imported_rank = _PACKAGE_RANK.get(imported_package)
            if imported_rank is None or imported_rank <= importer_rank:
                continue
            violations.append(
                f"{module_name} (rank {importer_rank}, package {importer_package}) "
                f"imports {imported} (rank {imported_rank}, package {imported_package})"
            )

    assert not violations, "Layering violation(s) found:\n" + "\n".join(violations)


def test_core_package_never_imports_services_or_api() -> None:
    """coding-guidelines.md § Layering, named explicitly: no `core` module
    imports `services` or `api` (routers)."""
    violations: list[str] = []

    for module_name, path in _iter_app_source_files():
        if _package_of(module_name) != "app.core":
            continue
        for imported in _imported_modules(module_name, path):
            if imported.startswith(("app.services", "app.api")):
                violations.append(f"{module_name} imports {imported}")

    assert not violations, "core must not import services/api:\n" + "\n".join(violations)
