"""
Report builder for novaHB.

Assembles all pipeline outputs into a single ImpactReport
and persists it to data/impact_report.json.

Pipeline:
    GitAnalysisResult
    → SemanticChange (from semantic_detector)
    → AffectedModules (from relevance_analyzer)
    → RoutingDecisions (from router)
    → ImpactReport
    → saved to disk + returned
"""
from __future__ import annotations

from .models import (
    CommitInfo,
    Developer,
    GitAnalysisResult,
    ImpactReport,
    SemanticChange,
)
from .relevance_analyzer import analyze_all_modules
from .router import route_all
from .semantic_detector import detect_semantic_change
from .storage import save_impact_report, load_developers
from . import models as m


def run_pipeline(git_result: GitAnalysisResult) -> ImpactReport:
    """
    Run the full analysis pipeline for a git commit result.
    Returns the complete ImpactReport and saves it to disk.
    """
    # Step 1: detect semantic change from diff
    semantic_change = detect_semantic_change(
        changed_files=git_result.changed_files,
        diff=git_result.diff,
    )

    # Step 2: determine which modules are affected and how
    affected_modules = analyze_all_modules(
        changed_files=git_result.changed_files,
        semantic_change=semantic_change,
    )

    # Step 3: load developers and produce routing decisions
    raw_devs = load_developers()
    developers = [Developer(**d) for d in raw_devs]
    routing = route_all(
        developers=developers,
        affected_modules=affected_modules,
        semantic_change=semantic_change,
        changed_files=git_result.changed_files,
    )

    # Step 4: assemble the report
    report = ImpactReport(
        commit=CommitInfo(
            id=git_result.commit_id[:8],  # short hash for display
            author=git_result.author,
            summary=git_result.message,
        ),
        semantic_change=semantic_change,
        affected_modules=affected_modules,
        routing=routing,
    )

    # Step 5: persist to disk
    save_impact_report(report.model_dump())

    return report
