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
            label="📋 Bu commiti bana özetle",
            answer=(
                f"**Commit `{commit_short}` — {author}**\n\n"
                f"{change_summary}\n\n"
                f"**Etkilenen dosyalar:** {', '.join(report.commit.summary.splitlines()[:1])}\n"
                f"**Kritiklik:** {report.semantic_change.criticality.value.upper()}\n"
                f"**Etkilenen alanlar:** {', '.join(report.semantic_change.domains)}\n\n"
                f"Bu değişiklik doğrudan senin görevini etkiliyor."
            ),
        ),
        NotificationQuestion(
            option_id="how_am_i_affected",
            label="🎯 Bu commit beni nasıl etkiler?",
            answer=(
                f"**Seni neden etkiliyor:**\n\n"
                f"{routing.reason}\n\n"
                f"**Senin mevcut görevin:** {dev.current_task}\n"
                f"**Risk altındaki dosyaların:** {', '.join(dev.current_task_files)}\n\n"
                f"⚠️ Bu değişiklik kodunda runtime hataya yol açabilir — "
                f"şu anda çalıştığın modülde null kontrol eksik."
            ),
        ),
        NotificationQuestion(
            option_id="what_should_i_do",
            label="🔧 Ne yapmam gerekiyor?",
            answer=(
                f"**Yapman gerekenler (öncelik sırasıyla):**\n\n"
                f"1. {routing.recommended_action}\n"
                f"2. Etkilenen dosyalarını (`{', '.join(dev.current_task_files)}`) "
                f"gözden geçir — null/None durumunu handle et\n"
                f"3. Değişikliği test et ve PR'ını güncelle\n"
                f"4. Ekibine bildirdiğini teyit et\n\n"
                f"🕐 Bu **ACTION** kararıdır — mümkün olan en kısa sürede harekete geç."
            ),
        ),
        NotificationQuestion(
            option_id="is_my_pr_blocked",
            label="🚦 Mevcut PR'ım etkileniyor mu?",
            answer=(
                f"**Evet, etkileniyor olabilir.**\n\n"
                f"Şu anda üzerinde çalıştığın dosyalar "
                f"(`{', '.join(dev.current_task_files)}`) bu committen etkilenen "
                f"modüllerle çakışıyor.\n\n"
                f"**Önerilen adımlar:**\n"
                f"- Branch'ini `main`/`develop` ile rebase et\n"
                f"- Conflict'leri resolve et\n"
                f"- CI/CD pipeline'ının geçtiğini doğrula\n\n"
                f"novaHB bu kararı {report.semantic_change.criticality.value.upper()} "
                f"kritiklik seviyesinde verdi — merge etmeden önce review al."
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
        parts.append(f"**Bob'un tespit ettiği kırık kontratlar:**\n\n{contracts_bullets}")

    parts.append(
        "**Potansiyel riskler:**\n\n"
        "- Mevcut user kayıtlarında `email` alanı boş olabilir → "
        "null kontrolsüz kod patlar\n"
        "- ORM / serializer'lar nullable field'ı farklı handle edebilir\n"
        "- Schema migration olmadan eski DB kayıtlarıyla uyumsuzluk oluşabilir\n"
        "- API response'larında `email: null` döner — frontend bunu bekliyor mu?"
    )

    safe_mods = ", ".join(
        m.module for m in report.affected_modules if m.status.value == "safe"
    ) or "yok"
    affected_mods = ", ".join(
        m.module for m in report.affected_modules if m.status.value == "affected"
    ) or "yok"
    parts.append(
        f"**Şu anda SAFE olan modüller:** {safe_mods}\n"
        f"**AFFECTED olan modüller:** {affected_mods}\n\n"
        "Tam güvenli merge için tüm affected modüller fix'lenmeli."
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
            label="📋 Bu commiti bana özetle",
            answer=(
                f"**Commit `{commit_short}` — {author}**\n\n"
                f"{report.semantic_change.summary}\n\n"
                f"**Kritiklik:** {report.semantic_change.criticality.value.upper()}\n"
                f"**Etkilenen domain'ler:** {', '.join(report.semantic_change.domains)}\n"
                f"**Kanıt dosyalar:** {', '.join(report.semantic_change.evidence)}\n\n"
                f"Uzmanlığın ({', '.join(dev.expertise)}) bu değişiklikle "
                f"doğrudan örtüşüyor — senin review'ın kritik."
            ),
        ),
        NotificationQuestion(
            option_id="how_am_i_affected",
            label="🎯 Bu commit beni nasıl etkiler?",
            answer=(
                f"**Neden senden review bekleniyor:**\n\n"
                f"{routing.reason}\n\n"
                f"**Uzmanlık alanların:** {', '.join(dev.expertise)}\n"
                f"**Sahip olduğun modüller:** {', '.join(dev.modules)}\n\n"
                f"Bu değişiklik schema/migration uyumluluğunu etkiliyor ve "
                f"senin ekspertizin bu konuda kritik."
            ),
        ),
        NotificationQuestion(
            option_id="what_should_i_do",
            label="🔧 Ne yapmam gerekiyor?",
            answer=(
                f"**Expert review için adımlar:**\n\n"
                f"1. {routing.recommended_action}\n"
                f"2. Backward compatibility'yi doğrula — mevcut kayıtlar etkileniyor mu?\n"
                f"3. Migration stratejisini gözden geçir\n"
                f"4. Approve veya request_changes kararını ver:\n"
                f"   ```\n"
                f"   POST /review/{dev.id}\n"
                f"   {{\"decision\": \"approve\"}}  veya  {{\"decision\": \"request_changes\"}}\n"
                f"   ```\n\n"
                f"⚡ Senin kararın merge sürecini bloke ediyor — öncelikli olarak ele al."
            ),
        ),
        NotificationQuestion(
            option_id="what_breaks_if_merged",
            label="💥 Merge edilirse ne bozulur?",
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
            label="📋 Bu commiti bana özetle",
            answer=(
                f"**Commit `{commit_short}` — {author}**\n\n"
                f"{report.semantic_change.summary}\n\n"
                f"**Kritiklik:** {report.semantic_change.criticality.value.upper()}\n"
                f"**Etkilenen domain'ler:** {', '.join(report.semantic_change.domains)}\n\n"
                f"ℹ️ Senin görevin bu değişiklikten **doğrudan etkilenmiyor** — "
                f"bu bir bilgilendirme notifikasyonudur."
            ),
        ),
        NotificationQuestion(
            option_id="how_am_i_affected",
            label="🎯 Bu commit beni nasıl etkiler?",
            answer=(
                f"**Neden SILENT kararı verildi:**\n\n"
                f"{routing.reason}\n\n"
                f"**Mevcut görevin:** {dev.current_task}\n\n"
                f"✅ Şu anda çalıştığın dosyalar (`{', '.join(dev.current_task_files) or 'yok'}`) "
                f"bu değişiklikten etkilenmiyor. Devam edebilirsin."
            ),
        ),
        NotificationQuestion(
            option_id="should_i_do_anything",
            label="✅ Yapmam gereken bir şey var mı?",
            answer=(
                f"**Şu an için yapman gereken bir şey yok.**\n\n"
                f"novaHB analizi:\n"
                f"- Modüllerin ya bu değişiklikten bağımsız ya da zaten güvenli\n"
                f"- Görevin (`{dev.current_task[:80]}`) bu değişiklikle çakışmıyor\n\n"
                f"**Öneri:** Ekibindeki diğer geliştiricilerin action durumunu "
                f"takip edebilirsin — merge sonrası sistemi etkileyebilecek bir "
                f"durum ortaya çıkarsa bildirim alacaksın."
            ),
        ),
        NotificationQuestion(
            option_id="who_is_handling_this",
            label="👥 Bu değişikliği kim handle ediyor?",
            answer=(
                f"**Aktif sorumlular:**\n\n"
                + "\n".join(
                    f"- **{r.developer_id}** → `{r.decision.value}`: {r.reason[:80]}{'...' if len(r.reason) > 80 else ''}"
                    for r in report.routing
                    if r.decision.value != "SILENT"
                )
                + (
                    "\n\n_(Şu an ACTION veya REVIEW_REQUIRED olan kimse yok)_"
                    if all(r.decision.value == "SILENT" for r in report.routing)
                    else ""
                )
                + f"\n\n**Toplam {len(report.routing)} geliştirici analiz edildi.** "
                f"Senin rolün şu an pasif — gerekirse bildirim alacaksın."
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
    "Format your answer in markdown. Be concise but complete. Use Turkish."
)

_QUESTION_LABELS = {
    "summarize_commit": "Bu commiti bana özetle",
    "how_am_i_affected": "Bu commit beni nasıl etkiler?",
    "what_should_i_do": "Ne yapmam gerekiyor?",
    "is_my_pr_blocked": "Mevcut PR'ım etkileniyor mu?",
    "what_breaks_if_merged": "Merge edilirse ne bozulur?",
    "should_i_do_anything": "Yapmam gereken bir şey var mı?",
    "who_is_handling_this": "Bu değişikliği kim handle ediyor?",
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

Answer their question in Turkish markdown. Be specific to their task and files.
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
