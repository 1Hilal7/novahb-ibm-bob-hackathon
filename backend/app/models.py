"""
Pydantic models for novaHB backend.

These are the shared data contracts for the entire pipeline:
  Git Commit → Semantic Change → Dependency Analysis → Routing → Impact Report
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


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
    broken_contracts: list[str] = Field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Interactive notification system
# ---------------------------------------------------------------------------

class NotificationQuestion(BaseModel):
    """
    A single interactive question a developer can select from their
    notification package. Includes both the label shown to the user
    and the pre-computed answer from the system.
    """
    option_id: str             # e.g. "summarize_commit", "how_am_i_affected"
    label: str                 # short question shown to developer, e.g. "📋 Bu commiti özetle"
    answer: str                # full markdown answer from the system


class NotificationPackage(BaseModel):
    """
    The full notification payload sent to a developer.
    Contains their routing decision + 4 interactive questions.
    Developer picks one question → system returns the answer.
    """
    developer_id: str
    decision: Decision
    reason: str
    recommended_action: Optional[str] = None
    commit_id: str
    commit_summary: str
    semantic_summary: str
    questions: list[NotificationQuestion]   # always 4 items


class AskRequest(BaseModel):
    """
    Request body when a developer selects a question from their notification.
    """
    option_id: str  # must match one of the option_ids in the notification package


class AskResponse(BaseModel):
    """
    System's answer to a developer's selected question.
    """
    developer_id: str
    option_id: str
    label: str
    answer: str
    decision: Decision
