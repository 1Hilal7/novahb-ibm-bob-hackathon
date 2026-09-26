"""
Git analyzer for novaHB.

Extracts commit metadata, changed files, and diff content from the
sample_repo git history using subprocess + Git CLI.

Security note: all git commands are passed as list arguments (no shell=True).
No user-supplied strings are interpolated into shell commands.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .models import GitAnalysisResult


# The git repository being analysed is the repo root itself
REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_git(args: list[str], cwd: Path = REPO_ROOT) -> str:
    """
    Run a git command in *cwd* and return stdout as a string.
    Raises RuntimeError if the command fails.
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
            f"git {' '.join(args)} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def get_head_commit_id(cwd: Path = REPO_ROOT) -> str:
    """Return the full SHA of HEAD."""
    return _run_git(["rev-parse", "HEAD"], cwd=cwd).strip()


def get_commit_author(commit_id: str, cwd: Path = REPO_ROOT) -> str:
    return _run_git(
        ["show", "-s", "--format=%an", commit_id], cwd=cwd
    ).strip()


def get_commit_message(commit_id: str, cwd: Path = REPO_ROOT) -> str:
    return _run_git(
        ["show", "-s", "--format=%s", commit_id], cwd=cwd
    ).strip()


def get_changed_files(commit_id: str, cwd: Path = REPO_ROOT) -> list[str]:
    """
    Return a list of files changed in *commit_id* relative to its parent.
    For the first commit (no parent), returns all tracked files.
    """
    # Try diff against parent
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit_id],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
    return []


def get_diff(commit_id: str, cwd: Path = REPO_ROOT) -> str:
    """
    Return the unified diff for *commit_id*.
    Falls back gracefully if the commit has no parent.
    """
    # Check if parent exists
    parent_result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit_id}^"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if parent_result.returncode == 0:
        try:
            return _run_git(["diff", f"{commit_id}^", commit_id], cwd=cwd)
        except RuntimeError:
            pass

    # First commit — show everything as an addition
    try:
        return _run_git(["show", commit_id], cwd=cwd)
    except RuntimeError:
        return ""


def analyze_commit(commit_id: str | None = None) -> GitAnalysisResult:
    """
    Analyse a specific commit (or HEAD if *commit_id* is None).

    Returns a GitAnalysisResult with commit metadata, changed files, and diff.
    Raises RuntimeError if the git repository or commit cannot be found.
    """
    if not (REPO_ROOT / ".git").exists():
        raise RuntimeError(f"No git repository found at {REPO_ROOT}")

    resolved_id = commit_id if commit_id else get_head_commit_id()

    author = get_commit_author(resolved_id)
    message = get_commit_message(resolved_id)
    changed_files = get_changed_files(resolved_id)
    diff = get_diff(resolved_id)

    return GitAnalysisResult(
        commit_id=resolved_id,
        author=author,
        message=message,
        changed_files=changed_files,
        diff=diff,
    )
