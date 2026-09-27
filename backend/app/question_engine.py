"""
Question Engine for novaHB — Interactive Notification System.

When a developer is notified about a commit's blast radius impact,
they receive a notification package containing:
  - Their routing decision (ACTION / REVIEW_REQUIRED / SILENT)
  - 4 interactive questions they can ask about the change

Each question is tailored to:
  - The developer's decision level (ACTION vs REVIEW_REQUIRED vs SILENT)
  - The semantic change context (what actually changed)
  - The developer's role and current task

The developer selects a question by its option_id and receives a
focused, actionable answer from the system.
"""
from __future__ import annotations

from .models import (
    Decision,
    Developer,
    ImpactReport,
    NotificationQuestion,
    NotificationPackage,
    RoutingDecision,
)


# ---------------------------------------------------------------------------
# Question builders — one set per decision level
# ---------------------------------------------------------------------------

def _build_action_questions(
    dev: Developer,
    routing: RoutingDecision,
    report: ImpactReport,
) -> list[NotificationQuestion]:
    """4 questions for ACTION developers — urgency-focused."""
    change_summary = report.semantic_change.summary
    commit_short = report.commit.id
    author = report.commit.author

    return [
        NotificationQuestion(
            option_id="summarize_commit",
            label="📋 Summarize this commit",
            answer=(
                f"**Commit `{commit_short}` — {author}**\n\n"
                f"{change_summary}\n\n"
                f"**Affected files:** {', '.join(report.semantic_change.evidence)}\n"
                f"**Criticality:** {report.semantic_change.criticality.value.upper()}\n"
                f"**Affected domains:** {', '.join(report.semantic_change.domains)}\n\n"
                f"This change directly affects your current task."
            ),
        ),
        NotificationQuestion(
            option_id="how_am_i_affected",
            label="🎯 How does this affect me?",
            answer=(
                f"**Why this affects you:**\n\n"
                f"{routing.reason}\n\n"
                f"**Your current task:** {dev.current_task}\n"
                f"**Files at risk:** {', '.join(dev.current_task_files)}\n\n"
                f"⚠️ This change may cause a runtime error in your code — "
                f"the module you are working on is missing a null guard."
            ),
        ),
        NotificationQuestion(
            option_id="what_should_i_do",
            label="🔧 What should I do?",
            answer=(
                f"**Recommended steps (in priority order):**\n\n"
                f"1. {routing.recommended_action}\n"
                f"2. Review the affected files (`{', '.join(dev.current_task_files)}`) "
                f"and handle the null/None case\n"
                f"3. Test the change and update your PR\n"
                f"4. Confirm the relevant team members are informed\n\n"
                f"🕐 This is an **ACTION** decision — address it as soon as possible."
            ),
        ),
        NotificationQuestion(
            option_id="is_my_pr_blocked",
            label="🚦 Is my current PR affected?",
            answer=(
                f"**Yes, it may be affected.**\n\n"
                f"The files you are currently working on "
                f"(`{', '.join(dev.current_task_files)}`) overlap with "
                f"modules affected by this commit.\n\n"
                f"**Recommended steps:**\n"
                f"- Rebase your branch onto `main`/`develop`\n"
                f"- Resolve any conflicts\n"
                f"- Verify that the CI/CD pipeline passes\n\n"
                f"novaHB bu kararı {report.semantic_change.criticality.value.upper()} "
                f"criticality — get a review before merging."
            ),
        ),
    ]


def _build_what_breaks_answer(report: ImpactReport) -> str:
    """
    Build the what_breaks_if_merged answer text.
    Prepends Bob's identified broken_contracts when available,
    then lists safe/affected modules. Falls back to generic risks if empty.
    """
    parts = []

    if report.semantic_change.broken_contracts:
        contracts_bullets = "\n".join(
            f"- {c}" for c in report.semantic_change.broken_contracts
        )
        parts.append(f"**Identified broken contracts:**\n\n{contracts_bullets}")

    parts.append(
        "**Potential risks:**\n\n"
        "- Mevcut user kayıtlarında `email` alanı boş olabilir → "
        "null kontrolsüz kod patlar\n"
        "- ORMs or serializers may handle the nullable field differently\n"
        "- Existing database records may become incompatible without a schema migration\n"
        "- API responses may return `email: null` — consumers must handle it"
    )

    safe_mods = ", ".join(
        m.module for m in report.affected_modules if m.status.value == "safe"
    ) or "none"
    affected_mods = ", ".join(
        m.module for m in report.affected_modules if m.status.value == "affected"
    ) or "none"
    parts.append(
        f"**Currently SAFE modules:** {safe_mods}\n"
        f"**AFFECTED modules:** {affected_mods}\n\n"
        "All affected modules should be addressed before a fully safe merge."
    )

    return "\n\n".join(parts)


def _build_review_required_questions(
    dev: Developer,
    routing: RoutingDecision,
    report: ImpactReport,
) -> list[NotificationQuestion]:
    """4 questions for REVIEW_REQUIRED developers — expert-focused."""
    commit_short = report.commit.id
    author = report.commit.author

    return [
        NotificationQuestion(
            option_id="summarize_commit",
            label="📋 Summarize this commit",
            answer=(
                f"**Commit `{commit_short}` — {author}**\n\n"
                f"{report.semantic_change.summary}\n\n"
                f"**Criticality:** {report.semantic_change.criticality.value.upper()}\n"
                f"**Affected domains:** {', '.join(report.semantic_change.domains)}\n"
                f"**Evidence files:** {', '.join(report.semantic_change.evidence)}\n\n"
                f"Your expertise ({', '.join(dev.expertise)}) bu değişiklikle "
                f"doğrudan örtüşüyor — senin review'ın kritik."
            ),
        ),
        NotificationQuestion(
            option_id="how_am_i_affected",
            label="🎯 How does this affect me?",
            answer=(
                f"**Why your review is required:**\n\n"
                f"{routing.reason}\n\n"
                f"**Your expertise:** {', '.join(dev.expertise)}\n"
                f"**Modules you own:** {', '.join(dev.modules)}\n\n"
                f"This change affects schema and migration compatibility, and "
                f"your expertise is important here."
            ),
        ),
        NotificationQuestion(
            option_id="what_should_i_do",
            label="🔧 What should I do?",
            answer=(
                f"**Expert review steps:**\n\n"
                f"1. {routing.recommended_action}\n"
                f"2. Verify backward compatibility — are existing records affected?\n"
                f"3. Review the migration strategy\n"
                f"4. Submit an approve or request_changes decision:\n"
                f"   ```\n"
                f"   POST /review/{dev.id}\n"
                f"   {{\"decision\": \"approve\"}}  or  {{\"decision\": \"request_changes\"}}\n"
                f"   ```\n\n"
                f"⚡ Your review is gating the merge — handle it as a priority."
            ),
        ),
        NotificationQuestion(
            option_id="what_breaks_if_merged",
            label="💥 What could break if this is merged?",
            answer=_build_what_breaks_answer(report),
        ),
    ]


def _build_silent_questions(
    dev: Developer,
    routing: RoutingDecision,
    report: ImpactReport,
) -> list[NotificationQuestion]:
    """4 questions for SILENT developers — awareness-focused."""
    commit_short = report.commit.id
    author = report.commit.author

    return [
        NotificationQuestion(
            option_id="summarize_commit",
            label="📋 Summarize this commit",
            answer=(
                f"**Commit `{commit_short}` — {author}**\n\n"
                f"{report.semantic_change.summary}\n\n"
                f"**Criticality:** {report.semantic_change.criticality.value.upper()}\n"
                f"**Affected domains:** {', '.join(report.semantic_change.domains)}\n\n"
                f"ℹ️ Your task is **not directly affected** by this change — "
                f"novaHB keeps you silent unless your attention becomes necessary."
            ),
        ),
        NotificationQuestion(
            option_id="how_am_i_affected",
            label="🎯 How does this affect me?",
            answer=(
                f"**Why you were kept SILENT:**\n\n"
                f"{routing.reason}\n\n"
                f"**Your current task:** {dev.current_task}\n\n"
                f"✅ Şu anda çalıştığın dosyalar (`{', '.join(dev.current_task_files) or 'none'}`) "
                f"are not affected by this change. You can continue your work."
            ),
        ),
        NotificationQuestion(
            option_id="should_i_do_anything",
            label="✅ Do I need to do anything?",
            answer=(
                f"**You do not need to take any action right now.**\n\n"
                f"novaHB analysis:\n"
                f"- Your modules are either unrelated to this change or already safe\n"
                f"- Your task (`{dev.current_task[:80]}`) does not conflict with this change\n\n"
                f"**Recommendation:** You can monitor the developers who currently require attention; "
                f"if the situation changes after the merge, "
                f"novaHB can route attention accordingly."
            ),
        ),
        NotificationQuestion(
            option_id="who_is_handling_this",
            label="👥 Who is handling this change?",
            answer=(
                f"**Developers currently handling the change:**\n\n"
                + "\n".join(
                    f"- **{r.developer_id}** → `{r.decision.value}`: {r.reason[:80]}{'...' if len(r.reason) > 80 else ''}"
                    for r in report.routing
                    if r.decision.value != "SILENT"
                )
                + (
                    "\n\n_(Şu an ACTION or REVIEW_REQUIRED olan kimse yok)_"
                    if all(r.decision.value == "SILENT" for r in report.routing)
                    else ""
                )
                + f"\n\n**A total of {len(report.routing)} developers were analyzed.** "
                f"Your attention is not required right now."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def build_notification_package(
    developer_id: str,
    report: ImpactReport,
) -> NotificationPackage:
    """
    Build a full notification package for a developer.

    Includes their routing decision + 4 context-aware questions
    they can ask the system about this commit's impact.
    """
    # Find developer's routing entry
    routing = next(
        (r for r in report.routing if r.developer_id == developer_id), None
    )
    if routing is None:
        raise ValueError(f"No routing entry found for developer '{developer_id}'")

    # Load developer profile from report context (we pass report + dev separately)
    # The caller must provide the Developer object
    return NotificationPackage(
        developer_id=developer_id,
        decision=routing.decision,
        reason=routing.reason,
        recommended_action=routing.recommended_action,
        commit_id=report.commit.id,
        commit_summary=report.commit.summary,
        semantic_summary=report.semantic_change.summary,
        questions=[],  # filled by build_questions_for_developer
    )


def build_questions_for_developer(
    dev: Developer,
    routing: RoutingDecision,
    report: ImpactReport,
) -> list[NotificationQuestion]:
    """
    Generate 4 interactive questions for this developer based on their decision.
    """
    if routing.decision == Decision.ACTION:
        return _build_action_questions(dev, routing, report)
    elif routing.decision == Decision.REVIEW_REQUIRED:
        return _build_review_required_questions(dev, routing, report)
    else:  # SILENT
        return _build_silent_questions(dev, routing, report)


def answer_question(
    question_id: str,
    dev: Developer,
    routing: RoutingDecision,
    report: ImpactReport,
) -> NotificationQuestion | None:
    """
    Find and return the question + answer for a given option_id.

    Strategy:
    1. Find the matching question template (validates option_id)
    2. Try to generate a personalized LLM answer (Gemini)
    3. Fall back to the pre-built hardcoded answer if LLM fails

    Returns None if the option_id is not valid for this developer's decision.
    """
    # Validate option_id by finding the template question
    template_questions = build_questions_for_developer(dev, routing, report)
    template = next((q for q in template_questions if q.option_id == question_id), None)
    if template is None:
        return None

    # Try LLM-generated personalized answer
    llm_answer = _generate_llm_answer(question_id, dev, routing, report)
    if llm_answer:
        return NotificationQuestion(
            option_id=template.option_id,
            label=template.label,
            answer=llm_answer,
        )

    # Fallback: return the pre-built hardcoded answer
    return template


# ---------------------------------------------------------------------------
# LLM answer generator
# ---------------------------------------------------------------------------

_ANSWER_SYSTEM = (
    "You are novaHB, an intelligent blast-radius analysis assistant. "
    "A developer has received a notification about a git commit that may affect their work. "
    "They selected a question to ask you. Give a clear, specific, actionable answer "
    "using their exact context (task, files, role). "
    "Format your answer in markdown. Be concise but complete. Use English."
)

_QUESTION_LABELS = {
    "summarize_commit": "Summarize this commit",
    "how_am_i_affected": "How does this affect me?",
    "what_should_i_do": "What should I do?",
    "is_my_pr_blocked": "Is my current PR affected?",
    "what_breaks_if_merged": "What could break if this is merged?",
    "should_i_do_anything": "Do I need to do anything?",
    "who_is_handling_this": "Who is handling this change?",
}

_ANSWER_PROMPT_TEMPLATE = """A developer received a notification about a git commit.
They selected the following question: "{question_label}"

Developer context:
- Name: {dev_name}
- Role: {dev_role}
- Expertise: {dev_expertise}
- Current task: {dev_task}
- Files they are working on: {dev_files}
- Routing decision: {decision}
- Why they were notified: {reason}
- Recommended action (from rule engine): {recommended_action}

Commit context:
- Commit ID: {commit_id}
- Commit message: {commit_summary}
- Semantic change: {semantic_summary}
- Criticality: {criticality}
- Affected domains: {domains}
- Affected modules: {affected_modules}

Other developers' decisions:
{other_decisions}

Answer their question in English markdown. Be specific to their task and files.
Do not be generic. Reference their actual situation.
"""


def _generate_llm_answer(
    question_id: str,
    dev: Developer,
    routing: RoutingDecision,
    report: ImpactReport,
) -> str | None:
    """
    Use Gemini to generate a personalized answer for the developer's question.
    Returns None on failure.
    """
    from .llm import call_llm, is_llm_available

    if not is_llm_available():
        return None

    other_decisions = "\n".join(
        f"- {r.developer_id}: {r.decision.value}"
        for r in report.routing
        if r.developer_id != dev.id
    )

    affected_modules_str = ", ".join(
        f"{m.module} ({m.status.value})" for m in report.affected_modules
    )

    prompt = _ANSWER_PROMPT_TEMPLATE.format(
        question_label=_QUESTION_LABELS.get(question_id, question_id),
        dev_name=dev.name,
        dev_role=dev.role,
        dev_expertise=", ".join(dev.expertise),
        dev_task=dev.current_task,
        dev_files=", ".join(dev.current_task_files) or "none",
        decision=routing.decision.value,
        reason=routing.reason,
        recommended_action=routing.recommended_action or "none",
        commit_id=report.commit.id,
        commit_summary=report.commit.summary,
        semantic_summary=report.semantic_change.summary,
        criticality=report.semantic_change.criticality.value,
        domains=", ".join(report.semantic_change.domains),
        affected_modules=affected_modules_str,
        other_decisions=other_decisions,
    )

    return call_llm(prompt, system=_ANSWER_SYSTEM, temperature=0.3)
