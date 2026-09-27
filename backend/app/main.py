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
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import (
    AnalyzeRequest,
    AskRequest,
    AskResponse,
    Developer,
    Decision,
    ImpactReport,
    NotificationPackage,
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
from .git_analyzer import analyze_commit, find_relevant_commit
from .report_builder import run_pipeline
from .question_engine import build_questions_for_developer, answer_question


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
# ---------------------------------------------------------------------------
# CORS — local development + production frontend
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://novahb.vercel.app",
    ],
    allow_origin_regex=r"https://.*\\.vercel\\.app",
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


@app.get("/llm/status", tags=["meta"])
def llm_status() -> dict:
    """
    Check whether the Gemini LLM is connected and available.
    Returns model name, availability status, and which pipeline stages use LLM.
    """
    from .llm import is_llm_available
    available = is_llm_available()
    return {
        "llm_available": available,
        "provider": "Google Gemini",
        "model": os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
        "stages": {
            "semantic_detection": "llm-first, deterministic fallback" if available else "deterministic only",
            "routing_enrichment": "llm-enriched" if available else "rule-engine only",
            "question_answers": "llm-personalized" if available else "pre-built templates",
        },
        "hint": None if available else "Set GEMINI_API_KEY in .env to enable LLM features",
    }


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

    If commit_id is not specified, uses the most recent commit that
    changed sample_repo/shared/user.py (the demo scenario target).
    Returns the ImpactReport and saves it to data/impact_report.json.
    """
    explicit_id = (request.commit_id if request else None) or None

    try:
        if explicit_id:
            commit_id = explicit_id
        else:
            # Default: find the most recent commit touching the demo target file
            commit_id = find_relevant_commit()
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


# ---------------------------------------------------------------------------
# Interactive Notification endpoints
# ---------------------------------------------------------------------------

@app.get("/notify/{developer_id}", response_model=NotificationPackage, tags=["notification"])
def get_notification(developer_id: str) -> NotificationPackage:
    """
    Get the notification package for a developer.

    Returns the developer's routing decision plus 4 interactive questions
    they can ask about the commit. The developer selects a question
    via POST /notify/{developer_id}/ask.

    Errors:
        404 — developer not found
        404 — no impact report yet (run POST /analyze first)
    """
    # Load impact report
    report_data = load_impact_report()
    if report_data is None:
        raise HTTPException(
            status_code=404,
            detail="No impact report found. Run POST /analyze first.",
        )
    report = ImpactReport(**report_data)

    # Validate developer exists
    raw_devs = load_developers()
    dev_data = next((d for d in raw_devs if d["id"] == developer_id), None)
    if dev_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Developer '{developer_id}' not found.",
        )
    dev = Developer(**dev_data)

    # Find routing decision
    routing = next(
        (r for r in report.routing if r.developer_id == developer_id), None
    )
    if routing is None:
        raise HTTPException(
            status_code=404,
            detail=f"No routing entry found for developer '{developer_id}'.",
        )

    # Build 4 context-aware questions
    questions = build_questions_for_developer(dev, routing, report)

    return NotificationPackage(
        developer_id=developer_id,
        decision=routing.decision,
        reason=routing.reason,
        recommended_action=routing.recommended_action,
        commit_id=report.commit.id,
        commit_summary=report.commit.summary,
        semantic_summary=report.semantic_change.summary,
        questions=questions,
    )


@app.post("/notify/{developer_id}/ask", response_model=AskResponse, tags=["notification"])
def ask_question(developer_id: str, body: AskRequest) -> AskResponse:
    """
    Developer selects a question from their notification package.

    The developer picks one of the 4 option_ids from GET /notify/{developer_id}
    and receives a focused, actionable answer from the system.

    Valid option_ids (depend on decision level):
      ACTION          : summarize_commit | how_am_i_affected | what_should_i_do | is_my_pr_blocked
      REVIEW_REQUIRED : summarize_commit | how_am_i_affected | what_should_i_do | what_breaks_if_merged
      SILENT          : summarize_commit | how_am_i_affected | should_i_do_anything | who_is_handling_this

    Errors:
        404 — developer not found
        404 — no impact report yet
        422 — invalid option_id for this developer's decision
    """
    # Load impact report
    report_data = load_impact_report()
    if report_data is None:
        raise HTTPException(
            status_code=404,
            detail="No impact report found. Run POST /analyze first.",
        )
    report = ImpactReport(**report_data)

    # Load developer
    raw_devs = load_developers()
    dev_data = next((d for d in raw_devs if d["id"] == developer_id), None)
    if dev_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Developer '{developer_id}' not found.",
        )
    dev = Developer(**dev_data)

    # Find routing decision
    routing = next(
        (r for r in report.routing if r.developer_id == developer_id), None
    )
    if routing is None:
        raise HTTPException(
            status_code=404,
            detail=f"No routing entry found for developer '{developer_id}'.",
        )

    # Answer the selected question
    result = answer_question(body.option_id, dev, routing, report)
    if result is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown option_id '{body.option_id}' for developer '{developer_id}' "
                f"with decision '{routing.decision.value}'. "
                f"Check GET /notify/{developer_id} for valid option_ids."
            ),
        )

    return AskResponse(
        developer_id=developer_id,
        option_id=result.option_id,
        label=result.label,
        answer=result.answer,
        decision=routing.decision,
    )
