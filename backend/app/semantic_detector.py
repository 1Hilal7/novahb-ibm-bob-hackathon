"""
Semantic change detector for novaHB (deterministic, no LLM).

For the demo scenario: detects when User.email changes from required (str)
to optional (str | None) by scanning the git diff content.

Future extension point: replace or augment with Bob/LLM reasoning.
If Bob/LLM call fails, this deterministic fallback always fires.
"""
from __future__ import annotations

import re

from .models import Criticality, SemanticChange


# ---------------------------------------------------------------------------
# Diff pattern detectors
# ---------------------------------------------------------------------------

# Patterns that indicate email becoming nullable
_NULLABLE_EMAIL_PATTERNS = [
    # Python type hint change: `email: str` → `email: str | None`
    re.compile(r"-\s+email:\s+str\b"),
    re.compile(r"\+\s+email:\s+str\s*\|\s*None"),
    # Optional[str] variants
    re.compile(r"\+\s+email:\s+Optional\[str\]"),
    re.compile(r"\+\s+email.*=\s*None"),
]

_SHARED_USER_FILE_PATTERNS = [
    "shared/user.py",
    "shared\\user.py",
]


def _diff_contains_nullable_email(diff: str) -> bool:
    """Return True if the diff shows email becoming nullable."""
    has_removal = bool(re.search(r"-\s+email:\s+str\b", diff))
    has_addition = bool(
        re.search(r"\+\s+email:\s+str\s*\|\s*None", diff)
        or re.search(r"\+\s+email:\s+Optional\[str\]", diff)
    )
    return has_removal and has_addition


def _changed_files_contain_shared_user(changed_files: list[str]) -> bool:
    """Return True if changed files include the shared user model."""
    for f in changed_files:
        normalized = f.replace("\\", "/")
        if any(pattern.replace("\\", "/") in normalized for pattern in _SHARED_USER_FILE_PATTERNS):
            return True
    return False


# ---------------------------------------------------------------------------
# Main detector
# ---------------------------------------------------------------------------

def detect_semantic_change(
    changed_files: list[str],
    diff: str,
) -> SemanticChange:
    """
    Analyse *changed_files* and *diff* to produce a SemanticChange.

    Detection hierarchy:
    1. User.email required → nullable (high criticality)
    2. Generic shared/user.py change (medium criticality)
    3. Fallback — unknown change (low criticality)
    """
    # Case 1: the demo scenario — email becomes nullable
    if _changed_files_contain_shared_user(changed_files) and _diff_contains_nullable_email(diff):
        return SemanticChange(
            summary="User email changed from required to optional",
            domains=["user-model", "database"],
            criticality=Criticality.HIGH,
            evidence=changed_files,
        )

    # Case 2: shared/user.py changed but pattern not matched
    if _changed_files_contain_shared_user(changed_files):
        return SemanticChange(
            summary="Shared User model was modified",
            domains=["user-model"],
            criticality=Criticality.MEDIUM,
            evidence=changed_files,
        )

    # Case 3: billing-related change
    billing_files = [f for f in changed_files if "billing" in f.lower()]
    if billing_files:
        return SemanticChange(
            summary="Billing module was modified",
            domains=["billing", "payments"],
            criticality=Criticality.MEDIUM,
            evidence=billing_files,
        )

    # Case 4: auth-related change
    auth_files = [f for f in changed_files if "auth" in f.lower()]
    if auth_files:
        return SemanticChange(
            summary="Auth module was modified",
            domains=["authentication", "security"],
            criticality=Criticality.MEDIUM,
            evidence=auth_files,
        )

    # Fallback
    return SemanticChange(
        summary=f"Code change detected in: {', '.join(changed_files) or 'unknown files'}",
        domains=["general"],
        criticality=Criticality.LOW,
        evidence=changed_files,
    )
