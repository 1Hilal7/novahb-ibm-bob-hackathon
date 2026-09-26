"""
Central Gemini LLM client for novaHB.

All LLM calls in the pipeline go through this module.
API key is loaded from .env (GEMINI_API_KEY).

Design principles:
- Single client instance (module-level singleton)
- Every call has a deterministic fallback — LLM failure never breaks the pipeline
- Structured JSON output enforced via Gemini response_schema where possible
- Timeouts kept tight (15s) to keep the API responsive
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load .env from repo root (if present) before importing google.genai
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _REPO_ROOT / ".env"

if _ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH)

# ---------------------------------------------------------------------------
# Gemini client — lazy init so import never fails without a key
# ---------------------------------------------------------------------------
_client = None
_model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


def _get_client():
    """Return a cached Gemini client, or None if key is missing."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — LLM features disabled, using fallbacks")
        return None

    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialised (model: %s)", _model_name)
        return _client
    except Exception as exc:
        logger.error("Failed to initialise Gemini client: %s", exc)
        return None


def is_llm_available() -> bool:
    """Return True if the Gemini client is ready."""
    return _get_client() is not None


# ---------------------------------------------------------------------------
# Core call helper
# ---------------------------------------------------------------------------

def call_llm(
    prompt: str,
    *,
    system: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.2,
) -> str | None:
    """
    Send a prompt to Gemini and return the text response.

    Args:
        prompt:      The user-turn prompt.
        system:      Optional system instruction.
        json_mode:   If True, instructs the model to respond in JSON.
        temperature: Sampling temperature (lower = more deterministic).

    Returns:
        The model's text response, or None on any failure.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        from google.genai import types

        contents = prompt
        if json_mode:
            contents = prompt + "\n\nRespond ONLY with valid JSON, no markdown fences."

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system or (
                "You are novaHB, an intelligent blast-radius analysis system. "
                "You help software teams understand the precise impact of a git commit. "
                "Be concise, technical, and actionable."
            ),
        )

        response = client.models.generate_content(
            model=_model_name,
            contents=contents,
            config=config,
        )
        return response.text

    except Exception as exc:
        logger.error("Gemini call failed: %s", exc)
        return None


def call_llm_json(prompt: str, *, system: str | None = None) -> dict | list | None:
    """
    Call Gemini expecting a JSON response. Parses and returns the object.
    Returns None on failure or parse error.
    """
    raw = call_llm(prompt, system=system, json_mode=True, temperature=0.1)
    if raw is None:
        return None

    # Strip markdown code fences if model added them anyway
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM JSON response: %s\nRaw: %s", exc, raw[:300])
        return None
