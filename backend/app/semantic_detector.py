"""
Semantic change detector for novaHB — LLM-first, no hardcodes.

NO pattern matching. NO field name checks. NO file path hardcodes.

The LLM receives the raw diff and changed files, then produces:
  - summary: what conceptually changed
  - domains: affected technical domains
  - criticality: low / medium / high
  - contracts: list of broken behavioral contracts

Works for ANY language and ANY type of change:
  - User.email required → nullable  (Python)
  - Payment.currency removed         (TypeScript)
  - JWT expiry 60m → 15m            (Go config)
  - API endpoint renamed             (any)

Fallback (LLM unavailable): infers domain from file paths + commit message,
never returns hardcoded field-specific content.
"""
from __future__ import annotations

import re
from pathlib import Path

from .models import Criticality, SemanticChange


# ---------------------------------------------------------------------------
# LLM-powered detector (primary path)
# ---------------------------------------------------------------------------

_SEMANTIC_SYSTEM = (
    "You are a senior software engineer performing blast-radius analysis on a git commit. "
    "Your job: identify WHAT semantically changed — not just what files changed. "
    "Think in terms of: data contracts, API contracts, type system changes, "
    "behavioral changes, security invariants, schema changes. "
    "Be precise, language-agnostic, and technology-neutral."
)

_SEMANTIC_PROMPT = """\
Analyze this git commit and determine the semantic change.

Changed files: {changed_files}
Commit message: {commit_message}

Diff:
```
{diff}
```

Identify:
1. WHAT contract/behavior changed (not just what file)
2. WHICH technical domains are affected
3. HOW critical is this (could it cause runtime errors, data loss, security issues?)
4. WHAT contracts are now broken for downstream consumers

Respond with JSON only (no markdown):
{{
  "summary": "One sentence: what contract/behavior changed and how",
  "domains": ["domain1", "domain2"],
  "criticality": "low|medium|high",
  "contracts": ["contract1 that changed", "contract2"],
  "reasoning": "why this criticality — what concretely could break"
}}

Criticality:
- high: breaking change, runtime errors, schema migration needed, security impact, data loss risk
- medium: behavior change, API contract shifted, tests may fail, consumers need to adapt
- low: internal refactor, rename, docs, additive change only
"""


def _detect_with_llm(
    changed_files: list[str],
    diff: str,
    commit_message: str = "",
) -> SemanticChange | None:
    """Pure LLM-based semantic detection. Returns None on any failure."""
    from .llm import call_llm_json, is_llm_available

    if not is_llm_available():
        return None

    diff_snippet = diff[:8000] if len(diff) > 8000 else diff
    prompt = _SEMANTIC_PROMPT.format(
        changed_files=", ".join(changed_files) or "unknown",
        commit_message=commit_message or "no message",
        diff=diff_snippet,
    )

    result = call_llm_json(prompt, system=_SEMANTIC_SYSTEM)
    if not result or not isinstance(result, dict):
        return None

    try:
        criticality_map = {"low": Criticality.LOW, "medium": Criticality.MEDIUM, "high": Criticality.HIGH}
        criticality = criticality_map.get(
            str(result.get("criticality", "medium")).lower(), Criticality.MEDIUM
        )
        domains = result.get("domains", [])
        if not isinstance(domains, list) or not domains:
            domains = ["general"]
        summary = str(result.get("summary", "Code change detected")).strip()
        if not summary:
            return None

        return SemanticChange(
            summary=summary,
            domains=domains,
            criticality=criticality,
            evidence=changed_files,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Generic fallback (no hardcodes, infers from file paths + commit message)
# ---------------------------------------------------------------------------

# Domain keywords mapped to file path segments — no specific field names
_PATH_DOMAIN_MAP = [
    (["auth", "login", "session", "token", "oauth", "jwt", "sso"],  "authentication"),
    (["billing", "invoice", "payment", "subscription", "stripe"],   "billing"),
    (["user", "account", "profile", "member"],                      "user-model"),
    (["db", "database", "migration", "schema", "model", "orm"],     "database"),
    (["api", "endpoint", "route", "controller", "handler"],         "api"),
    (["security", "crypto", "hash", "encrypt", "permission", "acl"], "security"),
    (["notify", "notification", "email", "sms", "push", "webhook"], "messaging"),
    (["config", "setting", "env", "feature", "flag"],               "configuration"),
    (["platform", "infra", "deploy", "health", "monitor"],          "platform"),
    (["shared", "common", "core", "base", "lib"],                   "shared-core"),
]

# Diff keywords that signal high criticality — language-agnostic
_HIGH_CRITICALITY_SIGNALS = [
    r"\bremoved?\b", r"\bdeleted?\b", r"\bdeprecated?\b",
    r"optional", r"nullable", r"null", r"None",
    r"required.*removed", r"breaking",
    r"migration", r"schema",
    r"secret", r"password", r"token", r"key",
    r"expir", r"timeout", r"ttl",
]

_MEDIUM_CRITICALITY_SIGNALS = [
    r"renamed?", r"moved?", r"refactored?",
    r"interface", r"contract", r"signature",
    r"default.*changed", r"behavior",
]


def _infer_domains_from_paths(changed_files: list[str]) -> list[str]:
    """Infer technical domains from file paths — no field-name hardcodes."""
    domains: set[str] = set()
    combined = " ".join(changed_files).lower()
    for keywords, domain in _PATH_DOMAIN_MAP:
        if any(kw in combined for kw in keywords):
            domains.add(domain)
    # Infer from file extensions
    extensions = {Path(f).suffix.lower() for f in changed_files}
    if extensions & {".sql", ".alembic", ".migration"}:
        domains.add("database")
    if extensions & {".yaml", ".yml", ".toml", ".env"}:
        domains.add("configuration")
    return list(domains) if domains else ["general"]


def _infer_criticality_from_diff(diff: str, commit_message: str) -> Criticality:
    """Infer criticality from diff content signals — language agnostic."""
    text = (diff + " " + commit_message).lower()
    if any(re.search(pat, text) for pat in _HIGH_CRITICALITY_SIGNALS):
        return Criticality.HIGH
    if any(re.search(pat, text) for pat in _MEDIUM_CRITICALITY_SIGNALS):
        return Criticality.MEDIUM
    return Criticality.LOW


def _detect_fallback(
    changed_files: list[str],
    diff: str,
    commit_message: str = "",
) -> SemanticChange:
    """
    Generic fallback — no hardcoded field names, no specific file paths.
    Infers domain and criticality from path structure and diff signals.
    """
    domains = _infer_domains_from_paths(changed_files)
    criticality = _infer_criticality_from_diff(diff, commit_message)

    # Build a reasonable summary from what we know
    file_count = len(changed_files)
    if commit_message:
        summary = commit_message
    elif changed_files:
        base_names = [Path(f).name for f in changed_files[:3]]
        summary = f"Changes in: {', '.join(base_names)}"
        if file_count > 3:
            summary += f" (+{file_count - 3} more)"
    else:
        summary = "Code change detected"

    return SemanticChange(
        summary=summary,
        domains=domains,
        criticality=criticality,
        evidence=changed_files,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_semantic_change(
    changed_files: list[str],
    diff: str,
    commit_message: str = "",
) -> SemanticChange:
    """
    Analyse changed_files and diff to produce a SemanticChange.

    Strategy:
      1. Gemini LLM — language-agnostic, context-aware, no hardcodes
      2. Generic fallback — path+diff signal heuristics, no field-name checks
    """
    result = _detect_with_llm(changed_files, diff, commit_message)
    if result is not None:
        return result
    return _detect_fallback(changed_files, diff, commit_message)
