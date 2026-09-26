"""
Relevance analyzer for novaHB.

Determines whether a dependent module actually requires action
when a change is made — or whether it is already safe.

This is the key differentiator:
    technically dependent != actually requires action

The analysis is based on real source code inspection using Python AST,
not hard-coded developer ID checks.

Module analysis results:
    "affected"  — the module has unsafe usage of the changed behavior
    "safe"      — the module handles the change safely (no action needed)
    "unrelated" — the module has no dependency on the changed area
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from .models import AffectedModule, ModuleStatus, SemanticChange
from .dependency_analyzer import get_dependents, module_imports_shared_user


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Source code safety checkers
# ---------------------------------------------------------------------------

def _find_python_files(module_path: str) -> list[Path]:
    """Return all .py files under a given module path (dir or single file)."""
    target = REPO_ROOT / module_path
    if target.is_file():
        return [target]
    if target.is_dir():
        return list(target.rglob("*.py"))
    return []


def _source_has_null_email_guard(file_path: Path) -> bool:
    """
    Return True if the file contains a None-guard or falsy-check for
    an attribute that looks like 'email' before using it.

    Patterns detected:
        if user.email is None: ...
        if not user.email: ...
        if user.email:  (used as guard)
        email is None check in any form
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return False

    for node in ast.walk(tree):
        # Pattern: `if X.email is None` or `if X.email is not None`
        if isinstance(node, (ast.If,)):
            test = node.test
            # `x.email is None`
            if isinstance(test, ast.Compare):
                if _is_email_attr(test.left):
                    for op, comp in zip(test.ops, test.comparators):
                        if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(comp, ast.Constant) and comp.value is None:
                            return True
            # `not x.email` or `not user.email`
            if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                if _is_email_attr(test.operand):
                    return True
            # bare `if x.email:` guards usage
            if _is_email_attr(test):
                return True

    return False


def _source_has_unsafe_email_usage(file_path: Path) -> bool:
    """
    Return True if the file uses a .email attribute WITHOUT a null guard
    in a way that would fail if email is None.

    Detected patterns:
        x.email.strip()       — method call on email attr
        x.email.lower()       — method call
        send_something(x.email, ...)  — email passed directly to a call
        f"...{x.email}..."    — string formatting without guard

    A file is only considered unsafe if it has email usage AND no null guard.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return False

    has_unsafe_usage = False
    for node in ast.walk(tree):
        # x.email.strip() or x.email.lower() — chained attribute access / call
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Attribute) and _is_email_attr(node.value):
                has_unsafe_usage = True

        # Function call where email attr is an argument: send_email(user.email, ...)
        if isinstance(node, ast.Call):
            for arg in node.args:
                if _is_email_attr(arg):
                    has_unsafe_usage = True

        # f-string that embeds email: f"...{user.email}..."
        if isinstance(node, ast.JoinedStr):
            for value in node.values:
                if isinstance(value, ast.FormattedValue) and _is_email_attr(value.value):
                    has_unsafe_usage = True

    return has_unsafe_usage


def _is_email_attr(node: ast.expr) -> bool:
    """Return True if *node* is an attribute access ending in 'email'."""
    return isinstance(node, ast.Attribute) and node.attr == "email"


# ---------------------------------------------------------------------------
# Per-module safety decision
# ---------------------------------------------------------------------------

def analyze_module_safety(
    module_id: str,
    module_path: str,
    semantic_change: SemanticChange,
) -> tuple[ModuleStatus, str, str]:
    """
    Analyse a single module and return (status, reason, evidence).

    The logic:
    1. Check if the module imports shared.user at all.
       If not → UNRELATED.
    2. If it depends on shared.user AND the change is about email nullability:
       a. Scan source for null guards → SAFE.
       b. Scan source for unsafe email usage → AFFECTED.
       c. If neither clearly applies, check the semantic domain for schema/database.
    """
    # Check if this is the changed module itself (shared-user)
    if module_id == "shared-user":
        return (
            ModuleStatus.UNRELATED,
            "This is the changed module itself, not a consumer",
            module_path,
        )

    # Does the module even import shared.user?
    imports_user = module_imports_shared_user(module_path)
    if not imports_user:
        return (
            ModuleStatus.UNRELATED,
            "Module does not import shared.user — no dependency on User model",
            module_path,
        )

    # The module depends on shared.user — now check safety
    py_files = _find_python_files(module_path)

    has_guard = any(_source_has_null_email_guard(f) for f in py_files)
    has_unsafe = any(_source_has_unsafe_email_usage(f) for f in py_files)

    if has_unsafe and not has_guard:
        return (
            ModuleStatus.AFFECTED,
            "Module uses User.email without null-guard — nullable email will cause runtime error",
            module_path,
        )

    if has_guard:
        return (
            ModuleStatus.SAFE,
            "Module already guards against nullable email — no action required",
            module_path,
        )

    # Default: dependent but no clear unsafe usage found
    return (
        ModuleStatus.SAFE,
        "Module depends on User but does not directly expose unsafe email usage",
        module_path,
    )


# ---------------------------------------------------------------------------
# Full analysis across all affected modules
# ---------------------------------------------------------------------------

def analyze_all_modules(
    changed_files: list[str],
    semantic_change: SemanticChange,
) -> list[AffectedModule]:
    """
    Given a list of changed files and the semantic change description,
    return AffectedModule entries for every module that is relevant.

    The changed module's dependents come from dependency_analyzer.
    The changed module itself is evaluated for criticality.
    """
    from .dependency_analyzer import get_module_for_file
    from .storage import load_project_map

    project_map = load_project_map()
    all_modules = {m["id"]: m for m in project_map.get("modules", [])}

    affected: list[AffectedModule] = []
    evaluated_ids: set[str] = set()

    for changed_file in changed_files:
        # Find which module was changed
        owning_id = get_module_for_file(changed_file)

        # Find which modules depend on it
        dependent_ids = get_dependents(changed_file)

        for dep_id in dependent_ids:
            if dep_id in evaluated_ids:
                continue
            evaluated_ids.add(dep_id)

            module_info = all_modules.get(dep_id, {})
            module_path = module_info.get("path", dep_id)

            status, reason, evidence = analyze_module_safety(
                dep_id, module_path, semantic_change
            )
            affected.append(
                AffectedModule(
                    module=dep_id,
                    status=status,
                    reason=reason,
                    evidence=evidence,
                )
            )

    return affected
