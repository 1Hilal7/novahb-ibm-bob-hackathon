"""
Git analyzer for novaHB.

Extracts commit metadata, changed files, and diff content from the
repository using subprocess + Git CLI.

The default novaHB demo targets the real historical nullable-email commit.
Production platforms may deploy with shallow Git history, so a fixture
captured from that real commit is used only when the canonical commit is
not available locally.

Security note:
- all git commands are passed as list arguments
- no shell=True
- no user-supplied strings are interpolated into shell commands
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import GitAnalysisResult


# ---------------------------------------------------------------------------
# Paths / demo configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

DEMO_TARGET_FILE = "sample_repo/shared/user.py"

# Canonical real commit used by the novaHB demo.
DEMO_COMMIT_PREFIX = "fafa0ce"

# When a deployment has shallow Git history, we use a snapshot captured
# from the real canonical commit instead of incorrectly analysing HEAD.
DEMO_FIXTURE_PATH = REPO_ROOT / "data" / "demo_nullable_email.json"

DEMO_FIXTURE_TOKEN = "__NOVAHB_DEMO_FIXTURE__"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _run_git(
    args: list[str],
    cwd: Path = REPO_ROOT,
) -> str:
    """
    Run a git command in cwd and return stdout.

    Raises RuntimeError when the command fails.
    """

    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed "
            f"(exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    return result.stdout


def _resolve_commit_if_available(
    commit_id: str,
    cwd: Path = REPO_ROOT,
) -> str | None:
    """
    Resolve commit_id to a full SHA if the commit exists
    in the currently available Git history.

    Returns None when the commit is unavailable.
    """

    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            f"{commit_id}^{{commit}}",
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    resolved = result.stdout.strip()

    return resolved or None


def get_head_commit_id(
    cwd: Path = REPO_ROOT,
) -> str:
    """Return the full SHA of HEAD."""

    return _run_git(
        ["rev-parse", "HEAD"],
        cwd=cwd,
    ).strip()


def get_commit_author(
    commit_id: str,
    cwd: Path = REPO_ROOT,
) -> str:
    return _run_git(
        [
            "show",
            "-s",
            "--format=%an",
            commit_id,
        ],
        cwd=cwd,
    ).strip()


def get_commit_message(
    commit_id: str,
    cwd: Path = REPO_ROOT,
) -> str:
    return _run_git(
        [
            "show",
            "-s",
            "--format=%s",
            commit_id,
        ],
        cwd=cwd,
    ).strip()


def get_changed_files(
    commit_id: str,
    cwd: Path = REPO_ROOT,
) -> list[str]:
    """
    Return files changed by commit_id.
    """

    result = subprocess.run(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "-r",
            "--name-only",
            commit_id,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )

    if (
        result.returncode == 0
        and result.stdout.strip()
    ):
        return [
            file_name.strip()
            for file_name
            in result.stdout.strip().splitlines()
            if file_name.strip()
        ]

    return []


def get_diff(
    commit_id: str,
    cwd: Path = REPO_ROOT,
) -> str:
    """
    Return unified diff for commit_id.
    """

    parent_result = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            f"{commit_id}^",
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )

    if parent_result.returncode == 0:
        try:
            return _run_git(
                [
                    "diff",
                    f"{commit_id}^",
                    commit_id,
                ],
                cwd=cwd,
            )
        except RuntimeError:
            pass

    try:
        return _run_git(
            ["show", commit_id],
            cwd=cwd,
        )
    except RuntimeError:
        return ""


# ---------------------------------------------------------------------------
# Production-safe demo fixture
# ---------------------------------------------------------------------------

def _load_demo_fixture() -> GitAnalysisResult:
    """
    Load the Git analysis snapshot captured from the real
    fafa0ce nullable-email commit.

    This is NOT a precomputed routing result.

    The normal semantic/dependency/routing pipeline still runs
    from this Git input exactly as it would for the real commit.
    """

    if not DEMO_FIXTURE_PATH.exists():
        raise RuntimeError(
            "Canonical demo commit is unavailable and "
            f"demo fixture was not found at "
            f"{DEMO_FIXTURE_PATH}"
        )

    try:
        data = json.loads(
            DEMO_FIXTURE_PATH.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load demo fixture: {exc}"
        ) from exc

    required = {
        "commit_id",
        "author",
        "message",
        "changed_files",
        "diff",
    }

    missing = required.difference(data)

    if missing:
        raise RuntimeError(
            "Demo fixture is malformed. "
            f"Missing fields: {sorted(missing)}"
        )

    return GitAnalysisResult(
        commit_id=data["commit_id"],
        author=data["author"],
        message=data["message"],
        changed_files=data["changed_files"],
        diff=data["diff"],
    )


# ---------------------------------------------------------------------------
# Demo commit resolution
# ---------------------------------------------------------------------------

def find_relevant_commit(
    target_file: str = DEMO_TARGET_FILE,
    cwd: Path = REPO_ROOT,
) -> str:
    """
    Resolve the commit to analyse.

    For the canonical novaHB demo:
      1. Prefer the real fafa0ce commit when full Git history exists.
      2. Otherwise use the fixture captured from that exact real commit.

    For other target files, use normal Git history lookup.

    This avoids shallow deployment history incorrectly treating
    the deployment HEAD as the demo change.
    """

    if target_file == DEMO_TARGET_FILE:
        canonical_commit = (
            _resolve_commit_if_available(
                DEMO_COMMIT_PREFIX,
                cwd=cwd,
            )
        )

        if canonical_commit:
            return canonical_commit

        if DEMO_FIXTURE_PATH.exists():
            return DEMO_FIXTURE_TOKEN

        raise RuntimeError(
            "Canonical novaHB demo commit "
            f"'{DEMO_COMMIT_PREFIX}' is unavailable "
            "and no production demo fixture exists."
        )

    result = subprocess.run(
        [
            "git",
            "log",
            "--format=%H",
            "-n",
            "1",
            "--",
            target_file,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )

    if (
        result.returncode != 0
        or not result.stdout.strip()
    ):
        raise RuntimeError(
            f"No commit found that changed "
            f"'{target_file}'."
        )

    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Public analysis API
# ---------------------------------------------------------------------------

def analyze_commit(
    commit_id: str | None = None,
) -> GitAnalysisResult:
    """
    Analyse a specific Git commit.

    When commit_id is the internal production demo token,
    loads the captured real demo commit input.

    Explicit user-provided commit IDs continue to use Git normally.
    """

    if commit_id == DEMO_FIXTURE_TOKEN:
        return _load_demo_fixture()

    if not (REPO_ROOT / ".git").exists():
        raise RuntimeError(
            f"No git repository found at {REPO_ROOT}"
        )

    resolved_id = (
        commit_id
        if commit_id
        else get_head_commit_id()
    )

    author = get_commit_author(
        resolved_id
    )

    message = get_commit_message(
        resolved_id
    )

    changed_files = get_changed_files(
        resolved_id
    )

    diff = get_diff(
        resolved_id
    )

    return GitAnalysisResult(
        commit_id=resolved_id,
        author=author,
        message=message,
        changed_files=changed_files,
        diff=diff,
    )