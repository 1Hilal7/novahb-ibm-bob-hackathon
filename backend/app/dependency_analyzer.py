"""
Dependency analyzer for novaHB.

Two sources of truth:
1. config/project_map.json — authoritative module → dependency mapping.
2. Python AST import scanning — confirms/enriches relationships at code level.

This is NOT a universal dependency engine.
Its job is to answer: "which modules depend on a changed file?"
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from .storage import load_project_map


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# project_map helpers
# ---------------------------------------------------------------------------

def get_dependents(changed_file: str) -> list[str]:
    """
    Given a changed file path (relative to repo root), return the list of
    module IDs from project_map.json that depend on the module containing
    that file.

    Example:
        changed_file = "sample_repo/shared/user.py"
        → ["billing", "notifications", "auth"]
    """
    project_map = load_project_map()
    modules = project_map.get("modules", [])

    # Find which module "owns" the changed file
    owning_module_ids = _find_owning_modules(changed_file, modules)

    if not owning_module_ids:
        return []

    # Find all modules that list any owning module in their depends_on
    dependents: list[str] = []
    for module in modules:
        for dep in module.get("depends_on", []):
            if dep in owning_module_ids and module["id"] not in dependents:
                dependents.append(module["id"])

    return dependents


def get_module_for_file(file_path: str) -> Optional[str]:
    """
    Return the project_map module ID that owns *file_path*, or None.
    """
    project_map = load_project_map()
    modules = project_map.get("modules", [])
    ids = _find_owning_modules(file_path, modules)
    return ids[0] if ids else None


def _find_owning_modules(file_path: str, modules: list[dict]) -> list[str]:
    """
    Return module IDs whose path prefix matches *file_path*.
    A module path may point to a file or a directory.
    """
    fp = Path(file_path)
    owned = []
    for module in modules:
        module_path = Path(module["path"])
        # Directory match: file is inside the module directory
        if module_path.suffix == "":
            # It's a directory path
            try:
                fp.relative_to(module_path)
                owned.append(module["id"])
            except ValueError:
                pass
        else:
            # It's a specific file
            if fp == module_path or str(fp) == str(module_path):
                owned.append(module["id"])
    return owned


# ---------------------------------------------------------------------------
# AST import scanning
# ---------------------------------------------------------------------------

def scan_imports(file_path: Path) -> list[str]:
    """
    Parse *file_path* with Python AST and return all imported module paths.
    Returns an empty list if the file cannot be parsed.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def module_imports_shared_user(module_path: str) -> bool:
    """
    Return True if ANY Python file inside *module_path* (or the file itself)
    imports from shared.user or sample_repo.shared.user.
    """
    target = REPO_ROOT / module_path
    py_files: list[Path] = []

    if target.is_file():
        py_files = [target]
    elif target.is_dir():
        py_files = list(target.rglob("*.py"))

    for py_file in py_files:
        imports = scan_imports(py_file)
        for imp in imports:
            if "shared.user" in imp or "shared" == imp:
                return True
    return False


def get_all_module_imports() -> dict[str, list[str]]:
    """
    For each module in project_map, scan its Python files and return
    a mapping of module_id → list of imported module strings.
    Useful for debugging and enriching context.
    """
    project_map = load_project_map()
    result: dict[str, list[str]] = {}

    for module in project_map.get("modules", []):
        module_path = REPO_ROOT / module["path"]
        py_files: list[Path] = []
        if module_path.is_file():
            py_files = [module_path]
        elif module_path.is_dir():
            py_files = list(module_path.rglob("*.py"))

        all_imports: list[str] = []
        for pf in py_files:
            all_imports.extend(scan_imports(pf))

        result[module["id"]] = list(set(all_imports))

    return result
