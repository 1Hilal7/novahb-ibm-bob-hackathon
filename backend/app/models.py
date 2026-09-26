"""
Pydantic models for novaHB backend.

These are the shared data contracts for the entire pipeline:
  Git Commit → Semantic Change → Dependency Analysis → Routing → Impact Report
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Decision(str, Enum):
    SILENT = "SILENT"
    ACTION = "ACTION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class Criticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModuleStatus(str, Enum):
    AFFECTED = "affected"
    SAFE = "safe"
    UNRELATED = "unrelated"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class Developer(BaseModel):
    id: str
    name: str
    role: str
    expertise: list[str]
    modules: list[str]
    current_task: str
    current_task_files: list[str]
    current_task_status: str


class ProjectModule(BaseModel):
    id: str
    path: str
    depends_on: list[str]


class ProjectMap(BaseModel):
    modules: list[ProjectModule]


# ---------------------------------------------------------------------------
# Commit / Git models
# ---------------------------------------------------------------------------

class CommitInfo(BaseModel):
    id: str
    author: str
    summary: str


class GitAnalysisResult(BaseModel):
    commit_id: str
    author: str
    message: str
    changed_files: list[str]
    diff: str


# ---------------------------------------------------------------------------
# Semantic change
# ---------------------------------------------------------------------------

class SemanticChange(BaseModel):
    summary: str
    domains: list[str]
    criticality: Criticality
    evidence: list[str]


# ---------------------------------------------------------------------------
# Affected modules
# ---------------------------------------------------------------------------

class AffectedModule(BaseModel):
    module: str
    status: ModuleStatus
    reason: str
    evidence: str


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

class RoutingDecision(BaseModel):
    developer_id: str
    decision: Decision
    reason: str
    recommended_action: Optional[str] = None


# ---------------------------------------------------------------------------
# Full impact report (final contract sent to frontend)
# ---------------------------------------------------------------------------

class ImpactReport(BaseModel):
    commit: CommitInfo
    semantic_change: SemanticChange
    affected_modules: list[AffectedModule]
    routing: list[RoutingDecision]


# ---------------------------------------------------------------------------
# Review flow
# ---------------------------------------------------------------------------

class ReviewAction(str, Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"


class ReviewRequest(BaseModel):
    decision: ReviewAction


class ReviewResult(BaseModel):
    developer_id: str
    decision: ReviewAction
    commit_id: str
    timestamp: str


# ---------------------------------------------------------------------------
# API request model for /analyze
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    commit_id: Optional[str] = None  # if None, use HEAD
