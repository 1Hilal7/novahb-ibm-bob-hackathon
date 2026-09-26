"""
Tests for the routing engine.

Tests 4-9: Validates the exact routing decisions for each developer.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from backend.app.git_analyzer import analyze_commit, find_relevant_commit
from backend.app.semantic_detector import detect_semantic_change
from backend.app.relevance_analyzer import analyze_all_modules
from backend.app.router import route_all
from backend.app.storage import load_developers
from backend.app.models import Developer, Decision, ModuleStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline_result():
    """Run the full pipeline once for all routing tests."""
    commit_id = find_relevant_commit()  # targets the nullable email demo commit
    git_result = analyze_commit(commit_id)
    sc = detect_semantic_change(git_result.changed_files, git_result.diff)
    affected = analyze_all_modules(git_result.changed_files, sc)
    raw_devs = load_developers()
    devs = [Developer(**d) for d in raw_devs]
    routing = route_all(devs, affected, sc, git_result.changed_files)
    return {
        "routing": {r.developer_id: r for r in routing},
        "affected": {m.module: m for m in affected},
        "semantic_change": sc,
    }


# ---------------------------------------------------------------------------
# Test 4: exactly 1 ACTION, 1 REVIEW_REQUIRED, 4 SILENT
# ---------------------------------------------------------------------------

def test_routing_decision_counts(pipeline_result):
    """Test 4: Routing must produce exactly 1 ACTION, 1 REVIEW_REQUIRED, 4 SILENT."""
    routing = list(pipeline_result["routing"].values())
    actions = [r for r in routing if r.decision == Decision.ACTION]
    reviews = [r for r in routing if r.decision == Decision.REVIEW_REQUIRED]
    silents = [r for r in routing if r.decision == Decision.SILENT]

    assert len(actions) == 1, f"Expected 1 ACTION, got {len(actions)}: {[r.developer_id for r in actions]}"
    assert len(reviews) == 1, f"Expected 1 REVIEW_REQUIRED, got {len(reviews)}: {[r.developer_id for r in reviews]}"
    assert len(silents) == 4, f"Expected 4 SILENT, got {len(silents)}: {[r.developer_id for r in silents]}"


# ---------------------------------------------------------------------------
# Test 5: Batuhan → ACTION
# ---------------------------------------------------------------------------

def test_batuhan_action(pipeline_result):
    """Test 5: Batuhan must receive ACTION decision."""
    decision = pipeline_result["routing"]["batuhan"]
    assert decision.decision == Decision.ACTION, \
        f"Expected ACTION for batuhan, got {decision.decision}"
    assert decision.recommended_action is not None, \
        "ACTION decision must include a recommended_action"


# ---------------------------------------------------------------------------
# Test 6: Emre → REVIEW_REQUIRED
# ---------------------------------------------------------------------------

def test_emre_review_required(pipeline_result):
    """Test 6: Emre must receive REVIEW_REQUIRED decision."""
    decision = pipeline_result["routing"]["emre"]
    assert decision.decision == Decision.REVIEW_REQUIRED, \
        f"Expected REVIEW_REQUIRED for emre, got {decision.decision}"
    assert decision.recommended_action is not None, \
        "REVIEW_REQUIRED must include a recommended_action"


# ---------------------------------------------------------------------------
# Test 7: Ayşe → SILENT
# ---------------------------------------------------------------------------

def test_ayse_silent(pipeline_result):
    """Test 7: Ayşe must receive SILENT decision (notifications already handles nullable email)."""
    decision = pipeline_result["routing"]["ayse"]
    assert decision.decision == Decision.SILENT, \
        f"Expected SILENT for ayse, got {decision.decision}"
    assert decision.recommended_action is None, \
        "SILENT must have null recommended_action"


# ---------------------------------------------------------------------------
# Test 8: Mert → SILENT
# ---------------------------------------------------------------------------

def test_mert_silent(pipeline_result):
    """Test 8: Mert must receive SILENT decision (platform has no user model dependency)."""
    decision = pipeline_result["routing"]["mert"]
    assert decision.decision == Decision.SILENT, \
        f"Expected SILENT for mert, got {decision.decision}"


# ---------------------------------------------------------------------------
# Test 9: Notifications module → safe
# ---------------------------------------------------------------------------

def test_notifications_safe(pipeline_result):
    """Test 9: Notifications module must be classified as SAFE (nullable email already handled)."""
    notifications_module = pipeline_result["affected"].get("notifications")
    assert notifications_module is not None, "Notifications module should appear in affected modules"
    assert notifications_module.status == ModuleStatus.SAFE, \
        f"Expected notifications to be SAFE, got {notifications_module.status}"


# ---------------------------------------------------------------------------
# Additional routing tests
# ---------------------------------------------------------------------------

def test_hilal_silent(pipeline_result):
    """Hilal must receive SILENT decision."""
    assert pipeline_result["routing"]["hilal"].decision == Decision.SILENT


def test_selin_silent(pipeline_result):
    """Selin must receive SILENT decision in the demo scenario."""
    assert pipeline_result["routing"]["selin"].decision == Decision.SILENT


def test_billing_affected(pipeline_result):
    """Billing module must be classified as AFFECTED."""
    billing = pipeline_result["affected"].get("billing")
    assert billing is not None, "Billing should appear in affected modules"
    assert billing.status == ModuleStatus.AFFECTED, \
        f"Expected billing to be AFFECTED, got {billing.status}"


def test_auth_safe(pipeline_result):
    """Auth module must be classified as SAFE."""
    auth = pipeline_result["affected"].get("auth")
    assert auth is not None, "Auth should appear in affected modules"
    assert auth.status == ModuleStatus.SAFE, \
        f"Expected auth to be SAFE, got {auth.status}"


def test_semantic_change_criticality_high(pipeline_result):
    """Semantic change for email→nullable must have HIGH criticality."""
    from backend.app.models import Criticality
    assert pipeline_result["semantic_change"].criticality == Criticality.HIGH


def test_all_6_developers_in_routing(pipeline_result):
    """All 6 developers must appear in the routing output."""
    expected = {"hilal", "batuhan", "ayse", "emre", "selin", "mert"}
    actual = set(pipeline_result["routing"].keys())
    assert actual == expected, f"Missing developers: {expected - actual}"


# ---------------------------------------------------------------------------
# broken_contracts tests
# ---------------------------------------------------------------------------

def test_semantic_change_broken_contracts_is_list(pipeline_result):
    """broken_contracts must always be a list (empty or populated)."""
    sc = pipeline_result["semantic_change"]
    assert isinstance(sc.broken_contracts, list), (
        f"Expected broken_contracts to be a list, got {type(sc.broken_contracts)}"
    )


def test_emre_review_reason_includes_contracts_when_present(pipeline_result):
    """When broken_contracts is non-empty, Emre's REVIEW_REQUIRED reason must reference them."""
    sc = pipeline_result["semantic_change"]
    if not sc.broken_contracts:
        # No LLM available in this environment — fallback produces empty list, skip
        import pytest
        pytest.skip("broken_contracts is empty (no LLM key in CI) — skipping contract-in-reason check")

    reason = pipeline_result["routing"]["emre"].reason
    # At least one contract text should appear in the reason
    assert any(c[:20] in reason for c in sc.broken_contracts), (
        f"Expected emre's reason to contain contract text.\n"
        f"Contracts: {sc.broken_contracts}\n"
        f"Reason: {reason}"
    )


def test_fallback_routing_decisions_unchanged(pipeline_result):
    """
    Core routing decisions must be deterministic regardless of broken_contracts.
    Even if broken_contracts is empty (fallback), counts must be 1/1/4.
    """
    routing = list(pipeline_result["routing"].values())
    from backend.app.models import Decision
    actions = [r for r in routing if r.decision == Decision.ACTION]
    reviews = [r for r in routing if r.decision == Decision.REVIEW_REQUIRED]
    silents = [r for r in routing if r.decision == Decision.SILENT]
    assert len(actions) == 1
    assert len(reviews) == 1
    assert len(silents) == 4


def test_semantic_change_serializes_broken_contracts():
    """SemanticChange with broken_contracts round-trips through JSON correctly."""
    from backend.app.models import SemanticChange, Criticality
    sc = SemanticChange(
        summary="test",
        domains=["user-model"],
        criticality=Criticality.HIGH,
        evidence=["shared/user.py"],
        broken_contracts=["User.email must be non-null", "API guarantees email present"],
    )
    data = sc.model_dump()
    assert data["broken_contracts"] == ["User.email must be non-null", "API guarantees email present"]

    # Round-trip via model
    sc2 = SemanticChange(**data)
    assert sc2.broken_contracts == sc.broken_contracts


def test_semantic_change_default_broken_contracts_empty():
    """SemanticChange without broken_contracts defaults to empty list."""
    from backend.app.models import SemanticChange, Criticality
    sc = SemanticChange(
        summary="test",
        domains=["general"],
        criticality=Criticality.LOW,
        evidence=[],
    )
    assert sc.broken_contracts == []


def test_impact_report_backward_compatible_without_broken_contracts():
    """ImpactReport constructed from data without broken_contracts must still parse."""
    from backend.app.models import (
        ImpactReport, CommitInfo, SemanticChange, Criticality,
        AffectedModule, ModuleStatus, RoutingDecision, Decision,
    )
    # Simulate old JSON that has no broken_contracts field
    sc_data = {
        "summary": "email nullable",
        "domains": ["user-model"],
        "criticality": "high",
        "evidence": ["shared/user.py"],
        # broken_contracts intentionally absent
    }
    sc = SemanticChange(**sc_data)
    assert sc.broken_contracts == []

    report = ImpactReport(
        commit=CommitInfo(id="abc12345", author="test", summary="make email nullable"),
        semantic_change=sc,
        affected_modules=[
            AffectedModule(module="billing", status=ModuleStatus.AFFECTED,
                           reason="unsafe", evidence="sample_repo/billing/"),
        ],
        routing=[
            RoutingDecision(developer_id="emre", decision=Decision.REVIEW_REQUIRED,
                            reason="schema owner"),
        ],
    )
    assert report.semantic_change.broken_contracts == []
