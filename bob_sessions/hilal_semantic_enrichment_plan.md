# Bob Semantic Enrichment Plan

## Top-Level Overview

**Goal:** Make IBM Bob's LLM reasoning a real, visible part of the analysis pipeline — not just a text enricher that runs after deterministic decisions are already fixed.

**Current state (grounded in code):**
- `semantic_detector.py` — LLM-first ✅ (Bob already does meaningful semantic analysis here)
- `router.py` / `_enrich_with_llm()` — LLM runs *after* decisions are made, enriches `reason` text only; routing outcome is 100% deterministic
- `relevance_analyzer.py` — 100% deterministic AST + import scanning; LLM has zero role
- `question_engine.py` / `_generate_llm_answer()` — LLM personalizes Q&A answers; good but downstream from routing

**The gap:** Bob already classifies the semantic change well, but that classification never feeds back into the routing *decision* logic. The router hard-codes domain names (`"user-model"`, `"shared-core"`) and contract strings. The LLM's `contracts` field from `SemanticChange` is parsed but never stored — it is discarded at the `SemanticChange` constructor boundary.

**Smallest high-value change:** Persist the LLM's `contracts` list on `SemanticChange` and surface it in the `ImpactReport`. Then use it in two places: (1) the router's `reason` text for REVIEW_REQUIRED decisions, and (2) the `what_breaks_if_merged` question answer in `question_engine.py`. This makes Bob's reasoning *observable* in the final output without changing any routing decision logic or the `ImpactReport` contract shape.

**Scope:** 3 files modified, 1 model field added (additive/optional — backward compatible), tests extended.

---

## Sub-Tasks

---

### Sub-Task 1 — Add `contracts` field to `SemanticChange`

**Status:** `[x] done`

**Intent:**
The LLM in `semantic_detector._detect_with_llm()` already asks for a `contracts` list ("what contracts are now broken for downstream consumers") and receives it from Gemini. The parsed value is silently discarded because `SemanticChange` has no field for it. Adding the field makes Bob's analysis visible end-to-end.

**Expected Outcomes:**
- `SemanticChange` gains an optional `contracts: list[str]` field (default `[]`).
- `_detect_with_llm()` populates it from the LLM response.
- `_detect_fallback()` leaves it empty (deterministic fallback unchanged).
- `ImpactReport.semantic_change.contracts` is present in the JSON response consumed by the frontend.
- No existing field changes name or type — the frontend receives additional data only.

**Todo List:**
1. In `backend/app/models.py`: add `contracts: list[str] = []` to `SemanticChange`.
2. In `backend/app/semantic_detector._detect_with_llm()`: extract `result.get("contracts", [])` and pass it when constructing `SemanticChange`.
3. Verify `_detect_fallback()` constructs `SemanticChange` without `contracts` (uses default) — no change needed.

**Relevant Context:**
- [`SemanticChange`](backend/app/models.py:83) — the model to extend.
- [`_detect_with_llm`](backend/app/semantic_detector.py:74) — where `contracts` is already parsed from LLM but ignored.
- [`_detect_fallback`](backend/app/semantic_detector.py:179) — must still work with no `contracts`.
- Frontend consumes `ImpactReport.semantic_change` — new optional field is additive and safe.

---

### Sub-Task 2 — Surface `contracts` in the router's REVIEW_REQUIRED reason

**Status:** `[x] done`

**Intent:**
The router's `route_developer()` produces a hard-coded `reason` string for REVIEW_REQUIRED decisions. With `contracts` now on `SemanticChange`, the deterministic reason can include the actual broken contracts identified by Bob. This makes the LLM analysis visibly contribute to what the expert sees in their notification — without changing the routing *decision* itself (still REVIEW_REQUIRED when the same conditions hold).

**Expected Outcomes:**
- REVIEW_REQUIRED `reason` text appends the contract list when `semantic_change.contracts` is non-empty.
- When `contracts` is empty (fallback mode), reason text is unchanged from current behavior.
- No change to `RoutingDecision` model shape.
- `_enrich_with_llm()` still runs afterward and can further personalize the text.

**Todo List:**
1. In `backend/app/router._build_review_required_reason()` (extract the inline reason string into a helper for clarity): if `semantic_change.contracts` is non-empty, append `"Broken contracts: {contracts}"` to the reason string.
2. Keep the existing hard-coded `recommended_action` string unchanged (it is correct and deterministic).

**Relevant Context:**
- [`route_developer`](backend/app/router.py:37) — the REVIEW_REQUIRED branch builds the reason inline at lines 63–75.
- [`SemanticChange.contracts`](backend/app/models.py:83) — source of truth after Sub-Task 1.
- [`_enrich_with_llm`](backend/app/router.py:270) — runs after, so enrichment still applies on top.

---

### Sub-Task 3 — Use `contracts` in the `what_breaks_if_merged` question answer

**Status:** `[x] done`

**Intent:**
`question_engine._build_review_required_questions()` builds the `what_breaks_if_merged` answer with a hard-coded bullet list of potential risks. With `contracts` available, the answer can include the specific broken contracts Bob identified — making the LLM's reasoning directly visible to the expert reviewer in the interactive Q&A.

**Expected Outcomes:**
- When `semantic_change.contracts` is non-empty, the `what_breaks_if_merged` answer prepends a "**Bob identified these broken contracts:**" section.
- When `contracts` is empty (fallback), the existing answer is shown unchanged.
- The LLM answer generator (`_generate_llm_answer`) already receives the full report — no change needed there.

**Todo List:**
1. In `backend/app/question_engine._build_review_required_questions()`: check `report.semantic_change.contracts`; if non-empty, prepend a contracts section to the `what_breaks_if_merged` answer.

**Relevant Context:**
- [`_build_review_required_questions`](backend/app/question_engine.py:100) — the `what_breaks_if_merged` answer is built at lines 152–168.
- [`ImpactReport.semantic_change`](backend/app/models.py:116) — carries `contracts` after Sub-Task 1.

---

### Sub-Task 4 — Add/update tests

**Status:** `[x] done`

**Intent:**
Preserve the existing test guarantees (routing counts, developer decisions, module safety) and add coverage for the new `contracts` field and its usage.

**Expected Outcomes:**
- All existing tests continue to pass without modification.
- New tests verify: (a) `SemanticChange.contracts` is a list, (b) when LLM is available the contracts list is non-empty for the demo scenario, (c) `ImpactReport` serializes and deserializes `contracts` correctly, (d) `what_breaks_if_merged` answer includes contracts text when contracts are present.

**Todo List:**
1. In `tests/test_routing.py`: add `test_semantic_change_has_contracts()` — asserts `pipeline_result["semantic_change"].contracts` is a `list` (may be empty in CI without API key; assert type only).
2. In `tests/test_api.py`: add `test_impact_report_semantic_change_schema()` — POST /analyze, assert response JSON includes `semantic_change.contracts` as a list (may be empty).
3. In `tests/test_routing.py`: add `test_emre_review_reason_references_contracts()` — when contracts non-empty, emre's reason must contain the word "contract" (case-insensitive). Skip if contracts list is empty (no API key in CI).

**Relevant Context:**
- [`test_routing.py`](tests/test_routing.py) — add to existing `pipeline_result` fixture.
- [`test_api.py`](tests/test_api.py) — extend `test_impact_latest_after_analyze` pattern.

---

## Impact Report Contract Preservation

The `ImpactReport` model shape does **not change**:
- No fields are removed or renamed.
- `SemanticChange.contracts` is a new **optional field with a default** (`list[str] = []`).
- Existing consumers that ignore unknown/new fields (standard JSON deserialization) are unaffected.
- The frontend receives richer data it can choose to render or ignore.

## Deterministic Fallback Preservation

All fallback paths remain intact:
- `_detect_fallback()` constructs `SemanticChange` without `contracts` — the default `[]` is used.
- Router REVIEW_REQUIRED reason: the contracts section is appended only `if contracts` — empty list → unchanged text.
- `question_engine` `what_breaks_if_merged`: contracts section only added `if report.semantic_change.contracts` — otherwise existing hard-coded answer is shown.
- `_enrich_with_llm()` in `router.py` is unchanged — it still runs after all deterministic decisions and enriches text.

## Files Modified

| File | Change |
|------|--------|
| `backend/app/models.py` | Add `contracts: list[str] = []` to `SemanticChange` |
| `backend/app/semantic_detector.py` | Populate `contracts` in `_detect_with_llm()` |
| `backend/app/router.py` | Append contracts to REVIEW_REQUIRED `reason` string |
| `backend/app/question_engine.py` | Prepend contracts to `what_breaks_if_merged` answer |
| `tests/test_routing.py` | Add 2 new tests |
| `tests/test_api.py` | Add 1 new test |

## Files NOT Modified

- `git_analyzer.py` — unchanged
- `dependency_analyzer.py` — unchanged
- `relevance_analyzer.py` — unchanged
- `report_builder.py` — unchanged
- `main.py` — unchanged
- `storage.py` — unchanged
- `llm.py` — unchanged
