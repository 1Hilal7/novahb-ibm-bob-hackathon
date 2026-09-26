"""
novaHB FastAPI backend.

Endpoints:
    GET  /health                     — liveness check
    GET  /project                    — project module map
    GET  /developers                 — all 6 developers
    POST /analyze                    — run full analysis pipeline
    GET  /impact/latest              — latest generated impact report
    POST /review/{developer_id}      — submit expert review (REVIEW_REQUIRED only)
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import (
    AnalyzeRequest,
    Developer,
    Decision,
    ImpactReport,
    ProjectMap,
    ReviewAction,
    ReviewRequest,
    ReviewResult,
)
from .storage import (
    load_developers,
    load_impact_report,
    load_project_map,
    load_reviews,
    save_reviews,
)
from .git_analyzer import analyze_commit
from .report_builder import run_pipeline


app = FastAPI(
    title="novaHB — Blast Radius Analyzer",
    description=(
        "Routes attention, not notifications. "
        "Determines which developer actually needs to act on a commit."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow frontend dev server (Vite default port)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe — always returns 200 if the server is running."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

@app.get("/project", response_model=ProjectMap, tags=["config"])
def get_project() -> ProjectMap:
    """Return the project module dependency map."""
    try:
        data = load_project_map()
        return ProjectMap(**data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="project_map.json not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load project map: {exc}")


# ---------------------------------------------------------------------------
# Developers
# ---------------------------------------------------------------------------

@app.get("/developers", response_model=list[Developer], tags=["config"])
def get_developers() -> list[Developer]:
    """Return all developer profiles."""
    try:
        raw = load_developers()
        return [Developer(**d) for d in raw]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="developers.json not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load developers: {exc}")


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------

@app.post("/analyze", response_model=ImpactReport, tags=["analysis"])
def analyze(request: Optional[AnalyzeRequest] = None) -> ImpactReport:
    """
    Run the full analysis pipeline for a commit.

    If commit_id is not specified, HEAD is used.
    Returns the ImpactReport and saves it to data/impact_report.json.
    """
    commit_id = (request.commit_id if request else None) or None

    try:
        git_result = analyze_commit(commit_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        report = run_pipeline(git_result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    return report


# ---------------------------------------------------------------------------
# Impact report
# ---------------------------------------------------------------------------

@app.get("/impact/latest", response_model=ImpactReport, tags=["analysis"])
def get_latest_impact() -> ImpactReport:
    """Return the most recently generated impact report."""
    data = load_impact_report()
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="No impact report found. Run POST /analyze first.",
        )
    try:
        return ImpactReport(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Malformed impact report: {exc}")


# ---------------------------------------------------------------------------
# Review endpoint
# ---------------------------------------------------------------------------

@app.post("/review/{developer_id}", response_model=ReviewResult, tags=["review"])
def submit_review(developer_id: str, body: ReviewRequest) -> ReviewResult:
    """
    Submit an expert review (approve / request_changes) for a developer
    who has a REVIEW_REQUIRED routing decision.

    Errors:
        404  — developer not found
        404  — no impact report yet
        409  — developer's decision is not REVIEW_REQUIRED
        422  — invalid review action
    """
    # Load current impact report
    report_data = load_impact_report()
    if report_data is None:
        raise HTTPException(
            status_code=404,
            detail="No impact report found. Run POST /analyze first.",
        )

    report = ImpactReport(**report_data)

    # Validate developer exists in the system
    raw_devs = load_developers()
    dev_ids = {d["id"] for d in raw_devs}
    if developer_id not in dev_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Developer '{developer_id}' not found.",
        )

    # Find developer's routing decision
    routing_entry = next(
        (r for r in report.routing if r.developer_id == developer_id), None
    )
    if routing_entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No routing entry found for developer '{developer_id}'.",
        )

    if routing_entry.decision != Decision.REVIEW_REQUIRED:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Developer '{developer_id}' has decision '{routing_entry.decision.value}', "
                f"not REVIEW_REQUIRED. Only REVIEW_REQUIRED developers can submit reviews."
            ),
        )

    # Build and persist review result
    review = ReviewResult(
        developer_id=developer_id,
        decision=body.decision,
        commit_id=report.commit.id,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    )

    reviews = load_reviews()
    # Update existing review for this developer+commit or append
    existing_idx = next(
        (
            i for i, r in enumerate(reviews)
            if r.get("developer_id") == developer_id and r.get("commit_id") == report.commit.id
        ),
        None,
    )
    review_dict = review.model_dump()
    if existing_idx is not None:
        reviews[existing_idx] = review_dict
    else:
        reviews.append(review_dict)

    save_reviews(reviews)

    return review
