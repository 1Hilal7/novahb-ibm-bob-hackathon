"""
API integration tests using FastAPI TestClient.

Tests 1-3, 11-12: HTTP endpoint tests.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import Decision, ImpactReport


client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: GET /health → 200
# ---------------------------------------------------------------------------

def test_health_endpoint():
    """Test 1: GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Test 2: GET /developers → exactly 6 developers
# ---------------------------------------------------------------------------

def test_developers_returns_6():
    """Test 2: GET /developers returns exactly 6 developers."""
    response = client.get("/developers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 6, f"Expected 6 developers, got {len(data)}"


def test_developers_have_required_fields():
    """Each developer must have all required model fields."""
    response = client.get("/developers")
    assert response.status_code == 200
    for dev in response.json():
        for field in ["id", "name", "role", "expertise", "modules",
                      "current_task", "current_task_files", "current_task_status"]:
            assert field in dev, f"Field '{field}' missing from developer {dev.get('id', '?')}"


# ---------------------------------------------------------------------------
# Test 3: POST /analyze → ImpactReport schema compliant
# ---------------------------------------------------------------------------

def test_analyze_returns_impact_report():
    """Test 3: POST /analyze returns a valid ImpactReport."""
    response = client.post("/analyze", json={})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    # Validate with Pydantic
    report = ImpactReport(**data)
    assert report.commit.id
    assert report.semantic_change.summary
    assert len(report.routing) == 6


def test_analyze_routing_counts():
    """Test 4 (via API): POST /analyze routing must have 1 ACTION, 1 REVIEW_REQUIRED, 4 SILENT."""
    response = client.post("/analyze", json={})
    assert response.status_code == 200
    data = response.json()
    routing = data["routing"]

    actions = [r for r in routing if r["decision"] == "ACTION"]
    reviews = [r for r in routing if r["decision"] == "REVIEW_REQUIRED"]
    silents = [r for r in routing if r["decision"] == "SILENT"]

    assert len(actions) == 1, f"Expected 1 ACTION, got {len(actions)}"
    assert len(reviews) == 1, f"Expected 1 REVIEW_REQUIRED, got {len(reviews)}"
    assert len(silents) == 4, f"Expected 4 SILENT, got {len(silents)}"


def test_analyze_batuhan_action_via_api():
    """Batuhan must receive ACTION via the API."""
    response = client.post("/analyze", json={})
    assert response.status_code == 200
    routing = {r["developer_id"]: r for r in response.json()["routing"]}
    assert routing["batuhan"]["decision"] == "ACTION"
    assert routing["batuhan"]["recommended_action"] is not None


def test_analyze_emre_review_required_via_api():
    """Emre must receive REVIEW_REQUIRED via the API."""
    response = client.post("/analyze", json={})
    assert response.status_code == 200
    routing = {r["developer_id"]: r for r in response.json()["routing"]}
    assert routing["emre"]["decision"] == "REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# GET /impact/latest
# ---------------------------------------------------------------------------

def test_impact_latest_after_analyze():
    """After /analyze, GET /impact/latest must return the stored report."""
    # Run analyze first
    client.post("/analyze", json={})
    response = client.get("/impact/latest")
    assert response.status_code == 200
    data = response.json()
    assert "commit" in data
    assert "routing" in data
    assert "semantic_change" in data



def test_analyze_semantic_change_has_broken_contracts_field():
    """POST /analyze response must include semantic_change.broken_contracts as a list."""
    response = client.post("/analyze", json={})
    assert response.status_code == 200
    data = response.json()
    sc = data.get("semantic_change", {})
    assert "broken_contracts" in sc, (
        "semantic_change must include broken_contracts field"
    )
    assert isinstance(sc["broken_contracts"], list), (
        f"broken_contracts must be a list, got {type(sc['broken_contracts'])}"
    )



# ---------------------------------------------------------------------------
# GET /project
# ---------------------------------------------------------------------------

def test_project_endpoint():
    """GET /project returns a valid project map with modules."""
    response = client.get("/project")
    assert response.status_code == 200
    data = response.json()
    assert "modules" in data
    assert len(data["modules"]) > 0


# ---------------------------------------------------------------------------
# Test 11: POST /review/emre approve → success
# ---------------------------------------------------------------------------

def test_review_emre_approve():
    """Test 11: POST /review/emre with approve returns 200."""
    # Run analyze to ensure impact report exists with REVIEW_REQUIRED for emre
    client.post("/analyze", json={})

    response = client.post("/review/emre", json={"decision": "approve"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    result = response.json()
    assert result["developer_id"] == "emre"
    assert result["decision"] == "approve"
    assert result["timestamp"]


def test_review_emre_request_changes():
    """POST /review/emre with request_changes returns 200."""
    client.post("/analyze", json={})
    response = client.post("/review/emre", json={"decision": "request_changes"})
    assert response.status_code == 200
    assert response.json()["decision"] == "request_changes"


# ---------------------------------------------------------------------------
# Test 12: Review on SILENT developer must return 409
# ---------------------------------------------------------------------------

def test_review_silent_developer_rejected():
    """Test 12: Sending review for a SILENT developer must return 409 Conflict."""
    client.post("/analyze", json={})
    # Batuhan is ACTION, not REVIEW_REQUIRED
    response = client.post("/review/batuhan", json={"decision": "approve"})
    assert response.status_code == 409, \
        f"Expected 409 for SILENT/ACTION developer, got {response.status_code}: {response.text}"


def test_review_mert_silent_rejected():
    """Mert is SILENT — review should be rejected with 409."""
    client.post("/analyze", json={})
    response = client.post("/review/mert", json={"decision": "approve"})
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

def test_review_unknown_developer_404():
    """Review for unknown developer ID returns 404."""
    client.post("/analyze", json={})
    response = client.post("/review/unknown-dev-xyz", json={"decision": "approve"})
    assert response.status_code == 404


def test_review_invalid_decision_422():
    """Invalid review decision returns 422 Unprocessable Entity."""
    client.post("/analyze", json={})
    response = client.post("/review/emre", json={"decision": "maybe"})
    assert response.status_code == 422
