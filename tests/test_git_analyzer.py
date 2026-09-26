"""
Tests for the git analyzer module.

Test 10: git analyzer can find the real changed file sample_repo/shared/user.py
"""
import sys
from pathlib import Path

# Ensure repo root is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from backend.app.git_analyzer import analyze_commit, get_head_commit_id, get_changed_files, find_relevant_commit


def test_git_analyzer_returns_result():
    """Git analyzer should return a result for the demo commit without error."""
    commit_id = find_relevant_commit()
    result = analyze_commit(commit_id)
    assert result is not None
    assert result.commit_id
    assert result.author
    assert result.message


def test_git_analyzer_finds_shared_user_change():
    """
    Test 10: The git analyzer must find sample_repo/shared/user.py
    as a changed file in the demo commit (nullable email change).
    """
    commit_id = find_relevant_commit()
    result = analyze_commit(commit_id)
    changed_normalized = [f.replace("\\", "/") for f in result.changed_files]
    assert any(
        "sample_repo/shared/user.py" in f for f in changed_normalized
    ), f"Expected sample_repo/shared/user.py in changed files, got: {result.changed_files}"


def test_git_analyzer_diff_not_empty():
    """Diff content should be non-empty for the demo commit."""
    commit_id = find_relevant_commit()
    result = analyze_commit(commit_id)
    assert result.diff.strip(), "Diff should not be empty"


def test_git_analyzer_diff_contains_nullable_email():
    """The diff for the demo commit should show email becoming nullable."""
    commit_id = find_relevant_commit()
    result = analyze_commit(commit_id)
    assert "str | None" in result.diff or "str|None" in result.diff or "Optional[str]" in result.diff, \
        "Diff should contain nullable email type annotation"


def test_git_analyzer_invalid_commit_raises():
    """Requesting an invalid commit ID should raise RuntimeError."""
    with pytest.raises(RuntimeError):
        analyze_commit("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
