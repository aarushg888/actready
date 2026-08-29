# ActReady v0.2 — ML/AI Scope & Plan

**Date:** 2026-08-29 · **Author:** Planning agent · **Status:** v0.2 scope-lock input
**Depends on:** `docs/ml-research.md`, `docs/research-deep-dive.md`, `docs/backend-research.md`, `docs/frontend-research.md`
**Core constraint (carried from ml-research §0):** the deterministic engine (`api/app/mapper.py`) is the system of record. ML is an assistive layer that *proposes*; it never *decides*. This is the single architectural rule that contains every risk in ml-research §5.

---

## 1. v0.2 ML scope decision

**ACCEPT exactly two features, both behind `ACTREADY_PROVIDER` (default off):**

- **(a) Evidence → control SUGGESTION** — given a free-text artifact, propose the controls/Articles it bears on (ml-research §1a). Implemented as a local embedding index + top-k retrieval, never an LLM verdict.
- **(b) Structured field EXTRACTION** — pull typed fields from model cards / incident reports into Pydantic schemas (ml-research §1b). Implemented as local LLM structured output with per-field confidence.

**DEFER to v0.3+ (explicitly rejected for v0.2):**
- **Risk-tier advisor** (ml-research §3) — highest legal exposure, needs counsel-reviewed disclaimer copy + regulatory snapshot pinning (Digital Omnibus Reg. 2026/1744). Decision maps to ML open question #5.
- **NL policy/remediation drafting** (ml-research §1d) — highest hallucination exposure; pure generation with no retrieval ground in our engine.
- **ML drift prediction** — the *classical* SPC drift detector (ml-research §2c) ships in v0.2 but as **core engine behavior, not an ML feature, and always-on with no flag** (backend-research §3 freshness; frontend-research §1a freshness strip). The ML-*augmented* trajectory predictor is deferred.

The existing `app/explain.py` already establishes the `ACTREADY_PROVIDER`='none' default pattern (ml-research §2). ML ships only when an operator sets the flag; out of the box the v0.1 deterministic engine is unmodified and remains the audit source of truth.

### Resolution of the ML brief's 8 open questions

1. **Threshold policy (OQ#1):** A control only "graduates" to suggestion UI once its golden-set per-control recall ≥ **0.90** (ml-research §4). This is enforced as a CI gate — not a runtime check. Per-control recall < 0.90 leaves the control in deterministic-only mode.
2. **Local-first vs API (OQ#2):** **Local-first is the default and the only path that ships with zero config.** `sentence-transformers/all-MiniLM-L6-v2` (CPU, 22M params) for embeddings; `ollama` (`llama3.2`) for extraction. A cloud provider (`openai`) is opt-in via `ACTREADY_PROVIDER=openai` and **never** sends evidence off-box unless that flag is set. Design partners get the air-gapped path first.
3. **Control-index ownership (OQ#3):** **ActReady ships a prebuilt, versioned control index** generated from `data/controls_iso42001.yaml` + `data/obligations_eu_ai_act.yaml` (the 39 ISO / 21 AI Act catalog). Users MAY supply an internal framework via a documented `actready reindex --catalog <path>` command; the index is regenerated and version-pinned. Default = our index.
4. **Override-rate SLA (OQ#4):** Sustained **>15% override rate on any control for 2 weeks** (or a regression vs. the prior model version) triggers a `REVIEW-MODEL` flag → auto-disable suggestions for that control + notify owner. Online override tracking (ml-research §4.2) makes this measurable.
5. **Classification scope (OQ#5):** **Defer** the EU AI Act risk-tier advisor to v0.3 (resolution above). The `REVIEW-COUNSEL` flag primitive is still built (§3) so v0.3 can reuse it.
6. **Drift signal source (OQ#6):** v0.2 consumes **`eval_run` metrics** (accuracy / faithfulness / robustness — Art. 15, A.6 V&V) that the deterministic engine already ingests (backend-research §2). SPC runs on that time series. No new signal source required for v0.2.
7. **Confidence calibration (OQ#7):** Suggestions use a **heuristic confidence** = cosine similarity + optional `bge-reranker` score (cheap, no API). Extraction uses **model-returned per-field confidence** from the structured-output call. Both are logged; thresholds are config, not code.
8. **Audit-log immutability (OQ#8):** The ML proposal log is **append-only, sha256-hash-chained**, mirroring `evidence_artifacts` immutability in backend-research §3.2. A `parent_evidence_hash` links every proposal to the exact artifact version it derived from, so an ISO 42001 auditor can replay proposal → human → confirmed.

---

## 2. Architecture — `app/ml/` module layout

All modules run with **zero API keys**. The provider layer collapses to `none` (deterministic short-circuit) by default.

```
api/app/ml/
├── __init__.py        # lazy imports; exposes get_provider()
├── providers.py       # Provider protocol: local (ollama) / openai / none
├── embed.py           # control-embedding index (MiniLM) + vector store (pgvector/Chroma)
├── classify.py        # evidence→control top-k suggestions + confidence + faithfulness check
├── extract.py         # LLM structured extraction + human-confirmation queue
└── schemas.py         # Pydantic: ModelCardFields, IncidentFields, Suggestion (§5)
```

**`providers.py`** — single `Provider` protocol (`embed(text)->vec`, `extract(prompt, schema)->obj`, `name`, `requires_key`). Three impls:
- `NoneProvider` — returns deterministic stubs; the v0.2 default, guarantees the test suite makes zero network calls (mirrors `explain.py` `_fake_explain`).
- `LocalProvider` — `sentence-transformers` for embed, `ollama`+`instructor` for extract. No key.
- `OpenAIProvider` — `instructor.from_openai`; only constructed when `ACTREADY_PROVIDER=openai`.

`get_provider()` reads `ACTREADY_PROVIDER` (default `none`) and returns the matching impl — same seam the rest of the app already uses.

**`embed.py`** — builds the curated control index **once** at startup from the YAML catalogs (OQ#3), encodes each control/Article clause with MiniLM (384-dim), stores vectors in **pgvector if Postgres is present, else Chroma** (backend-research §1.2 already assumes Postgres + SQLAlchemy; Chroma is the laptop fallback). Evidence chunks are embedded at request time; cosine top-k (with optional `bge-reranker` rerank) returns candidate controls.

**`classify.py`** — `suggest(evidence) -> list[Suggestion]`. Each `Suggestion` carries `control_id`, `similarity`, `rerank_score`, `confidence`, and a `citation` (the source chunk text + control catalog id). It runs a **faithfulness pre-check** (RAGAS `ContextRecall`/`Faithfulness` style) so a suggestion with no retrievable grounding is dropped. Output is a *proposal*, never written to `control_mappings`.

**`extract.py`** — `extract(artifact_text, schema) -> ExtractionResult`. Uses `instructor` to fill `ModelCardFields`/`IncidentFields`; every field carries `value` + `confidence` + `review_flag`. Low-confidence fields are queued in a **human-confirmation table** (`ml_extraction_queue`) and rendered as drafts, never as evidence state.

---

## 3. Safety guards — every ML output is a PROPOSAL

1. **Stored with confidence + citation.** Every suggestion/extraction row records `confidence`, the source chunk, and the model+version fingerprint (ml-research §5 reproducibility).
2. **Shown to a human, requires confirm.** Proposals live in `ml_proposals` / `ml_extraction_queue`. Promoting a proposal to a real `control_mapping` or `evidence_artifact` requires an explicit human action (or a logged, user-defined automation rule). The deterministic mapper stays the audit source of truth.
3. **Logged & immutable.** Proposal log is append-only + sha256-chained (OQ#8). Audit trail always shows `proposal → human → confirmed`.
4. **Citation-backed.** No proposal ships without a traceable source chunk + logged model call (ml-research §4 "if it isn't traceable, it doesn't ship").
5. **`REVIEW-COUNSEL` flag.** Reserved flag (built now, used in v0.3) for risk-tier/legal-exposure outputs; surfaces the "not legal advice" banner from ml-research §3 inline in the per-control drawer (frontend-research §1d).
6. **Visual distinction.** Frontend renders ML proposals with a distinct "AI-proposed" treatment separate from confirmed state (ml-research §5 over-trust risk), matching the existing `REVIEW-COUNSEL` surfacing decision (frontend-research OQ#8: inline-in-drawer).

---

## 4. Eval — golden dataset in CI

Three layers (ml-research §4), all wired into CI:

1. **Golden set (offline, gated).** Versioned corpus of `(evidence_text → expected_control_ids)` curated by the team + an auditor advisor. CI runs `classify.suggest` against it and asserts **per-control recall ≥ 0.90** (OQ#1) and overall F1 threshold. A merge that drops a control below 0.90 is blocked — same discipline as the engine's pytest suite.
2. **Human-agreement / override-rate (online).** Every proposal logs confirm/override; we track **override rate per control and per model version** (OQ#4 SLA: >15% over 2 weeks → `REVIEW-MODEL` flag + auto-disable).
3. **Control-coverage recall.** Recall is weighted on *missing* mappings (false negatives = unmet obligations) so a control with no evidence is never silently "passed."

**Frameworks adopted (don't reinvent):** **RAGAS** (`Faithfulness`/`ContextRecall`) for grounding of suggestions + extractions; **DeepEval** for pytest-style threshold assertions in CI (`HallucinationMetric`); **Giskard** for robustness/bias scanning of the extraction schema. Drift (classical SPC) needs no LLM-judge — numpy/pandas only (ml-research §2c).

---

## 5. Prompts / schemas (sketch)

```python
# schemas.py
class Suggestion(BaseModel):
    control_id: str                 # e.g. "A.7.2" or "EU-AI-ACT-A10"
    similarity: float               # cosine, 0..1
    rerank_score: float | None      # bge-reranker, if enabled
    confidence: float               # heuristic: similarity + rerank
    source_chunk: str               # grounded text (RAGAS Faithfulness)
    citation: str                   # control catalog id + clause

class ModelCardFields(BaseModel):
    model_name: FieldWithConf
    version: FieldWithConf
    intended_use: FieldWithConf
    eval_metrics: list[FieldWithConf]
    data_governance: FieldWithConf | None

class IncidentFields(BaseModel):
    incident_date: FieldWithConf
    severity: FieldWithConf         # low|med|high|critical
    affected_article: FieldWithConf | None   # e.g. "Art. 73"
    detection_ts: FieldWithConf
    corrective_action: FieldWithConf

class FieldWithConf(BaseModel):     # every extracted field is confidence-tagged
    value: str | None
    confidence: float
    review_flag: bool = Field(default=False)  # True when confidence < threshold
```

`FieldWithConf` is the unit that powers the `REVIEW` queue (ml-research §1b). Extraction prompts are few-shot (serialized JSON examples) and mandate returning `confidence` per field; suggestions carry the source chunk so faithfulness is mechanically checkable.

---

## 6. GitHub-issue-shaped tickets (grouped by epic)

**Epic A — Provider & config foundation**
- **A1. Provider protocol + `get_provider()` seam.** AC: `providers.py` defines `Provider` protocol with `NoneProvider`/`LocalProvider`/`OpenAIProvider`; `ACTREADY_PROVIDER='none'` (default) short-circuits with zero imports of `instructor`/`openai`/`sentence-transformers`. Effort: M.
- **A2. Local embed model wiring.** AC: MiniLM loads lazily; `embed()` returns 384-dim vectors with no API key; unit test on 3 control strings. Effort: M.
- **A3. Vector store adapter (pgvector | Chroma).** AC: `embed.py` stores/queries the control index; uses pgvector when Postgres DSN present, else Chroma; cosine top-k returns ≥1 result. Effort: M.

**Epic B — Control embedding index**
- **B1. Index builder from YAML catalogs.** AC: `actready build-index` encodes `data/controls_iso42001.yaml` + `obligations_eu_ai_act.yaml` into the store; version-stamped. Effort: S.
- **B2. Optional `bge-reranker` rerank.** AC: reranker re-scores top-k when enabled via flag; degrades gracefully if model absent. Effort: S.
- **B3. `reindex --catalog <path>` for customer frameworks.** AC: accepts external control YAML, rebuilds index, version-pins. Effort: M.

**Epic C — Evidence→control suggestion**
- **C1. `suggest()` with confidence + citation.** AC: returns `list[Suggestion]` with similarity, confidence, source_chunk, citation; deterministic stub when provider=none. Effort: M.
- **C2. RAGAS faithfulness pre-check.** AC: suggestions with no retrievable grounding are dropped; covered by a unit test. Effort: M.
- **C3. Per-control recall gate (≥0.90).** AC: CI job computes per-control recall on golden set; blocks merge below threshold. Effort: M.

**Epic D — Structured extraction**
- **D1. `extract()` for ModelCard + Incident.** AC: fills `ModelCardFields`/`IncidentFields` via `instructor`+Pydantic; local ollama path works with no key. Effort: M.
- **D2. Per-field confidence + `REVIEW` queue.** AC: `FieldWithConf.review_flag` set below threshold; rows land in `ml_extraction_queue` as drafts, never as evidence. Effort: M.
- **D3. Human-confirm → promote flow.** AC: confirming a queued extraction writes a real (immutable) `evidence_artifact`; old draft stays. Effort: L.

**Epic E — Safety / audit logging**
- **E1. `ml_proposals` append-only + hash chain.** AC: new table, sha256-chained to `parent_evidence_hash`; no UPDATE/DELETE (mirror backend §3.2). Effort: M.
- **E2. `REVIEW-COUNSEL` flag primitive + banner.** AC: flag column + UI banner text ("not legal advice"); reusable by v0.3 risk-tier. Effort: S.
- **E3. Override-rate SLA monitor.** AC: tracks confirm/override per control+model version; >15%/2wk → `REVIEW-MODEL` + auto-disable. Effort: M.

**Epic F — Eval & CI**
- **F1. Golden dataset scaffold + harness.** AC: versioned `(text→controls)` corpus + pytest runner emitting per-control precision/recall/F1. Effort: M.
- **F2. DeepEval/Giskard CI integration.** AC: `HallucinationMetric` + schema robustness scan run in CI; fail on regression. Effort: M.
- **F3. Online override-rate dashboard hook.** AC: exposes override-rate per control to the status endpoint (backend §5.2). Effort: S.

**Epic G — Frontend proposal surfaces**
- **G1. "AI-proposed" badge on suggestions.** AC: proposals visually distinct from confirmed state in Control Library / drawer. Effort: S.
- **G2. Extraction confirmation drawer.** AC: renders `ml_extraction_queue` drafts with per-field confidence; confirm/edit before promote. Effort: M.

**Totals:** 21 tickets (3 S, 15 M, 3 L). Risk-tier advisor, NL drafting, and ML drift prediction are intentionally absent — deferred to v0.3 per §1.
