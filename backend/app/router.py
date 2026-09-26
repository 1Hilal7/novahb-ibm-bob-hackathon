"""
Routing engine for novaHB.

Takes affected_modules, all developers, and semantic_change as input.
Produces a RoutingDecision for every developer.

Decision logic (deterministic rule engine):
- REVIEW_REQUIRED: criticality is high AND developer expertise matches the
  semantic domain AND developer owns the changed module or is actively
  working on schema/migration tasks.
- ACTION: module is AFFECTED AND developer is currently working on files
  in that module OR their active task directly overlaps the affected behavior.
- SILENT: everything else — including safe modules, unrelated modules, and
  cases where the developer is technically nearby but not actually impacted.

Key invariant:
    module ownership alone does NOT trigger ACTION.
    Task overlap + module safety together determine the decision.
"""
from __future__ import annotations

from .models import (
    AffectedModule,
    Developer,
    ModuleStatus,
    Decision,
    Criticality,
    RoutingDecision,
    SemanticChange,
)


# ---------------------------------------------------------------------------
# Routing rules
# ---------------------------------------------------------------------------

def route_developer(
    developer: Developer,
    affected_modules: list[AffectedModule],
    semantic_change: SemanticChange,
    changed_files: list[str],
) -> RoutingDecision:
    """
    Produce a RoutingDecision for one developer.
    Evaluated in priority order: REVIEW_REQUIRED → ACTION → SILENT.
    """

    # Build lookup: module_id → AffectedModule
    module_map: dict[str, AffectedModule] = {m.module: m for m in affected_modules}

    # Gather modules the developer owns that appear in affected list
    dev_affected_modules = [
        module_map[mid] for mid in developer.modules if mid in module_map
    ]

    # -- REVIEW_REQUIRED check ------------------------------------------
    # Condition: criticality is HIGH AND semantic domain overlaps with
    # developer expertise AND developer is actively responsible for the
    # changed domain (e.g., schema / database).
    if semantic_change.criticality == Criticality.HIGH:
        domain_match = _has_domain_match(developer, semantic_change)
        if domain_match and _is_schema_responsible(developer, changed_files):
            return RoutingDecision(
                developer_id=developer.id,
                decision=Decision.REVIEW_REQUIRED,
                reason=(
                    f"The shared User schema changed (required → optional email) "
                    f"and {developer.name} is responsible for schema migration "
                    f"and backward compatibility. Expert review is required."
                ),
                recommended_action=(
                    "Review backward compatibility, migration behavior, "
                    "and persisted user records."
                ),
            )

    # -- ACTION check -----------------------------------------------------
    # Condition: at least one of the developer's modules is AFFECTED AND
    # the developer's current_task_files overlap with that module's files.
    for mod in dev_affected_modules:
        if mod.status == ModuleStatus.AFFECTED:
            task_overlap = _has_task_overlap(developer, mod)
            if task_overlap:
                return RoutingDecision(
                    developer_id=developer.id,
                    decision=Decision.ACTION,
                    reason=(
                        f"{developer.name} is actively working on "
                        f"{_task_files_str(developer)} which depends on "
                        f"User.email, and the module has unsafe email usage "
                        f"without null-guard. The nullable email change will "
                        f"cause a runtime error in the current task."
                    ),
                    recommended_action=(
                        "Add explicit missing-email handling to invoice delivery "
                        "and update invoice tests."
                    ),
                )

    # -- SILENT -----------------------------------------------------------
    reason = _build_silent_reason(developer, dev_affected_modules, semantic_change)
    return RoutingDecision(
        developer_id=developer.id,
        decision=Decision.SILENT,
        reason=reason,
        recommended_action=None,
    )


# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------

def _has_domain_match(developer: Developer, semantic_change: SemanticChange) -> bool:
    """Return True if any semantic domain matches developer expertise."""
    # Data-model changes are a natural review boundary for schema and
    # migration owners even when a generic detector reports the domain as
    # "user-model" or "shared-core" rather than the literal word "schema".
    data_model_domains = {"user-model", "shared-core", "database"}
    schema_expertise = {"database", "schema", "migrations"}
    if data_model_domains.intersection(semantic_change.domains) and schema_expertise.intersection(
        developer.expertise
    ):
        return True

    for domain in semantic_change.domains:
        domain_lower = domain.lower()
        for exp in developer.expertise:
            if exp.lower() in domain_lower or domain_lower in exp.lower():
                return True
    return False


def _is_schema_responsible(developer: Developer, changed_files: list[str]) -> bool:
    """
    Return True if the developer is actively working on the changed files
    or owns the schema/database/shared domain explicitly.
    """
    # Direct file overlap with current task
    for task_file in developer.current_task_files:
        for changed in changed_files:
            # Normalize paths for comparison
            if (
                task_file.replace("\\", "/") in changed.replace("\\", "/")
                or changed.replace("\\", "/").endswith(task_file.replace("\\", "/"))
            ):
                return True

    # Developer explicitly owns 'shared' module (schema owner)
    if "shared" in developer.modules:
        schema_expertise = {"database", "schema", "migrations"}
        if schema_expertise.intersection(set(developer.expertise)):
            return True

    return False


def _has_task_overlap(developer: Developer, affected_module: AffectedModule) -> bool:
    """
    Return True if the developer's current_task_files are inside
    the affected module's path.
    """
    module_path = affected_module.evidence  # e.g. "sample_repo/billing/"
    for task_file in developer.current_task_files:
        tf_normalized = task_file.replace("\\", "/")
        mp_normalized = module_path.replace("\\", "/").rstrip("/")
        # The task file should be within the module's directory
        if tf_normalized in mp_normalized or mp_normalized.endswith(tf_normalized.split("/")[0]):
            return True
        # Check module name appears in task file path
        module_name = mp_normalized.split("/")[-1]  # e.g. "billing"
        if module_name and module_name in tf_normalized:
            return True
    return False


def _task_files_str(developer: Developer) -> str:
    return ", ".join(developer.current_task_files) or "their assigned files"


def _build_silent_reason(
    developer: Developer,
    dev_affected_modules: list[AffectedModule],
    semantic_change: SemanticChange,
) -> str:
    """Build a human-readable reason for a SILENT decision."""
    if not dev_affected_modules:
        return (
            f"No modules owned by {developer.name} are affected by this change. "
            f"Current task ({developer.current_task[:60]}...) has no dependency "
            f"on the User.email field."
        )

    safe_modules = [m for m in dev_affected_modules if m.status == ModuleStatus.SAFE]
    if safe_modules:
        mod_names = ", ".join(m.module for m in safe_modules)
        return (
            f"{developer.name}'s module(s) ({mod_names}) depend on User but "
            f"already handle nullable email safely — no code change required."
        )

    return (
        f"Current task for {developer.name} does not require action "
        f"for this email-nullable change."
    )


# ---------------------------------------------------------------------------
# Route all developers (deterministic)
# ---------------------------------------------------------------------------

def route_all(
    developers: list[Developer],
    affected_modules: list[AffectedModule],
    semantic_change: SemanticChange,
    changed_files: list[str],
) -> list[RoutingDecision]:
    """
    Produce a RoutingDecision for every developer.
    All 6 developers appear in output — SILENT decisions are explicit.

    Strategy:
    1. Run deterministic rule engine for all developers (always works)
    2. If LLM is available, enrich ACTION/REVIEW_REQUIRED decisions with
       Gemini-generated reasoning and recommended actions
    """
    decisions = [
        route_developer(dev, affected_modules, semantic_change, changed_files)
        for dev in developers
    ]

    # Try to enrich non-SILENT decisions with LLM reasoning
    enriched = _enrich_with_llm(decisions, developers, semantic_change, affected_modules)
    return enriched


# ---------------------------------------------------------------------------
# LLM enrichment for routing decisions
# ---------------------------------------------------------------------------

_ROUTING_SYSTEM = (
    "You are novaHB, a blast-radius analysis system. "
    "You produce precise, developer-specific impact notifications for git commits. "
    "Be direct, technical, and actionable. Use the developer's context."
)

_ROUTING_ENRICH_PROMPT = """A git commit was analyzed and routing decisions were made.
Enrich the reasoning and recommended_action for each non-SILENT developer.

Semantic change: {semantic_summary}
Criticality: {criticality}
Affected modules: {affected_modules}

Developers needing enrichment:
{developers_json}

For each developer, respond with a JSON array (no markdown fences):
[
  {{
    "developer_id": "<id>",
    "reason": "<personalized, specific reason why this developer is affected — reference their actual task and files>",
    "recommended_action": "<concrete step-by-step action they should take>"
  }}
]

Be specific about their current task and files. Do not be generic.
"""


def _enrich_with_llm(
    decisions: list[RoutingDecision],
    developers: list[Developer],
    semantic_change: SemanticChange,
    affected_modules: list[AffectedModule],
) -> list[RoutingDecision]:
    """
    Use Gemini to enrich reason and recommended_action for ACTION and
    REVIEW_REQUIRED developers. SILENT decisions are left untouched.
    Returns the (possibly enriched) decisions list.
    """
    from .llm import call_llm_json, is_llm_available
    import json as _json

    if not is_llm_available():
        return decisions

    # Only enrich non-SILENT decisions
    non_silent = [d for d in decisions if d.decision != Decision.SILENT]
    if not non_silent:
        return decisions

    dev_map = {d.id: d for d in developers}

    # Build context payload for LLM
    devs_payload = []
    for decision in non_silent:
        dev = dev_map.get(decision.developer_id)
        if dev is None:
            continue
        devs_payload.append({
            "developer_id": dev.id,
            "name": dev.name,
            "role": dev.role,
            "decision": decision.decision.value,
            "current_task": dev.current_task,
            "current_task_files": dev.current_task_files,
            "modules": dev.modules,
            "expertise": dev.expertise,
            "rule_engine_reason": decision.reason,
        })

    if not devs_payload:
        return decisions

    prompt = _ROUTING_ENRICH_PROMPT.format(
        semantic_summary=semantic_change.summary,
        criticality=semantic_change.criticality.value,
        affected_modules=", ".join(
            f"{m.module} ({m.status.value})" for m in affected_modules
        ),
        developers_json=_json.dumps(devs_payload, indent=2),
    )

    result = call_llm_json(prompt, system=_ROUTING_SYSTEM)
    if not result or not isinstance(result, list):
        return decisions

    # Apply enrichments
    enrichment_map = {item["developer_id"]: item for item in result if isinstance(item, dict)}
    enriched_decisions = []
    for decision in decisions:
        enrichment = enrichment_map.get(decision.developer_id)
        if enrichment and decision.decision != Decision.SILENT:
            enriched_decisions.append(RoutingDecision(
                developer_id=decision.developer_id,
                decision=decision.decision,
                reason=str(enrichment.get("reason", decision.reason)),
                recommended_action=str(enrichment.get("recommended_action", decision.recommended_action or "")),
            ))
        else:
            enriched_decisions.append(decision)

    return enriched_decisions
