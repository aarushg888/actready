# ActReady — ML/AI Research Brief

**Date:** 2026-08-29 · **Author:** ML research subagent · **Status:** v0.1 planning input
**Scope:** Where ML helps AI governance, defensible approaches/libs, EU AI Act risk-tier classification, evaluation, and risks. Research only — no code.

---

## 0. Framing: the deterministic engine is the source of truth

ActReady v0.1 is a **rule-based, deterministic** engine: it maps evidence files to controls by file *type* + *freshness*, with no ML inference in the core. That design is a feature, not a limitation. Governance is an audit discipline — auditors want reproducible, attributable, citation-backed mappings they can defend to a regulator. A black-box LLM judgment ("this evidence satisfies Article 10") is a *liability* in that context: the auditor cannot explain how the conclusion was reached, cannot reproduce it, and inherits model hallucination risk.

The thesis of this brief: **ML is defensible in ActReady only as an assistive layer that proposes, never decides.** Every ML output must be (1) human-in-the-loop confirmed, (2) fully logged with inputs/outputs/model/version, and (3) citation-backed to EUR-Lex or an internal catalog entry. The deterministic engine remains the default and the system of record; ML features sit behind an `ACTREADY_PROVIDER` flag (default off), mirroring the pattern already described in `research-brief.md`.

---

## 1. Where ML actually helps vs. hurts governance

### (a) Auto-classifying free-text evidence into control mappings — HELPS
A user uploads a free-text artifact (a policy PDF, an incident post-mortem, a model card). The deterministic engine keys off filename/extension/freshness. ML can *read the text* and propose which controls (Article 9–15, ISO 42001 clauses) the evidence bears on.
- **Why acceptable to auditors:** The proposal is surfaced for human confirmation before it affects any compliance state; the raw text, the chosen control IDs, the embedding similarity scores, and the model/version are all logged. The auditor sees *proposed* mappings, not auto-applied ones.
- **Why it hurts if done wrong:** If the system auto-applies mappings with no human gate, an auditor cannot defend a missed-or-wrong control mapping. Keep it advisory.

### (b) Extracting structured fields from model cards / incident reports / policies (NER + schema fill) — HELPS
Model cards and incident reports are semi-structured prose. ML can extract fields into a schema (model name, version, intended use, eval metrics, incident severity, affected article) — the kind of NER + schema-fill task LLMs do well.
- **Why acceptable:** Output is a draft record; confidence score per field; low-confidence fields flagged `REVIEW`. Human confirms. This is the same "structured extraction with human confirmation" pattern used in production document pipelines.
- **Why it hurts if done wrong:** Silent extraction errors (a wrong date, a misread severity) propagate into the evidence trail. Mitigate with field-level confidence + mandatory review on low scores.

### (c) Drift / anomaly detection on production eval metrics feeding the freshness window — HELPS (and is the *least* risky ML use)
ActReady's freshness window currently ages evidence by date. ML/statistics can watch a time series of eval scores (accuracy, faithfulness, safety metrics) and flag when a metric drifts outside control limits — triggering a freshness re-check or a control re-opening.
- **Why acceptable:** This is *classical* statistical process control (SPC), not a black box. The "model" is a control chart (mean ± 3σ, run rules). It makes no governance *judgment*; it only raises an alert ("eval faithfulness dropped 14% week-over-week") for a human to act on. Lowest hallucination exposure of all four.
- **Why it hurts if done wrong:** False positives create alert fatigue; false negatives miss real degradation. Use conservative thresholds + log every trigger.

### (d) Natural-language remediation hints / policy drafting — HELPS, with heavy disclaimers
Given an open control, ML can draft remediation guidance or a policy section in natural language, grounded in the relevant article text.
- **Why acceptable:** Purely assistive writing aid; never a legal conclusion. Every generated sentence must cite the source article/control and carry a "not legal advice" disclaimer (see §3).
- **Why it hurts if done wrong:** A confident-but-wrong drafted policy cited to an auditor as authoritative is the single highest-risk misuse. Treat output as a *starting draft*, never as approved language.

**Where ML hurts, full stop:** any place it replaces the deterministic mapping as the system of record, or renders a binding risk-tier or compliance verdict without human confirmation. That is the line we do not cross.

---

## 2. Specific approaches & libraries

### Evidence classification (a, b)
- **Embedding model + vector store.** Encode a *curated control-embedding index* (each control/Article clause embedded once) and compare against embedded evidence chunks.
  - **Open-weight embeddings (self-host, no API key):** `BAAI/bge-small-en-v1.5` (384-dim, MIT license, top MTEB score for its size-class) or `sentence-transformers/all-MiniLM-L6-v2` (384-dim, 22M params, ubiquitous, fast on CPU). For better accuracy on English, `bge-base-en-v1.5` is a cheap upgrade. `bge-m3` if multilingual is needed.
  - **Vector store:** `pgvector` (Postgres extension) if ActReady already runs Postgres — keeps embeddings next to relational evidence/control data, one source of truth, BSD license, no new infrastructure. Otherwise `Chroma` (lightweight, embedded, good for laptop/local prototyping). Both support HNSW/cosine search and run fully offline.
  - **Optional rerank:** a cross-encoder like `BAAI/bge-reranker` re-ranks the top-k for precision; improves mapping recall without an API call.
- **Few-shot prompting with structured output.** For classification/extraction that needs reasoning, use `instructor` (Pydantic-based structured-output library, 15+ providers incl. Ollama/local) or raw OpenAI structured outputs. Define a Pydantic schema (control ID, confidence, rationale, citations) and let the model fill it. Few-shot examples serialized as JSON in the prompt improve consistency.
  - **Local option:** run `ollama` with `llama3.2` or a small instruction model; `instructor.from_provider("ollama/...")` gives the same Pydantic interface with zero API dependency. This keeps ActReady air-gapable.

### Field extraction (b)
- LLM structured extraction (`instructor` + Pydantic) returning per-field `confidence`. Persist the raw extracted object + the prompt + model fingerprint. Human confirms or edits; the edit delta is logged as the authoritative record.

### Drift detection (c)
- **Statistical Process Control** on eval-score time series: compute rolling mean/σ, plot Shewhart control charts, apply Western Electric run rules (e.g., 1 point beyond 3σ, 9 consecutive on one side of centerline). Pure numpy/pandas — no model training, fully reproducible, deterministic.
- **Optional ML augmentation (later):** trajectory-based drift prediction (multivariate covariance) *alongside* classical SPC, never replacing it. UNVERIFIED — this is a v0.3+ candidate, not v0.2.

### Remediation / policy drafting (d)
- Same `instructor` + Pydantic pipeline as extraction, but output is free text constrained by a prompt that mandates citations. Gate behind `ACTREADY_PROVIDER` and the disclaimer from §3.

**Provider abstraction:** one `LLMProvider` interface (`openai`, `anthropic`, `ollama`, `groq`) selected by `ACTREADY_PROVIDER`. Default = none (deterministic only). This avoids vendor lock-in (see §5).

---

## 3. EU AI Act high-risk classification — should ActReady auto-classify?

**Short answer: advisory-only, never binding.** ActReady may *propose* a risk tier (unacceptable / high / limited / minimal) from a free-text system description, but the output must be explicitly non-deterministic, human-confirmed, and disclaimer-wrapped.

**Lawful-basis inputs (what the classifier should consume):**
- **Article 5** — prohibited practices → "unacceptable" if any match (social scoring, untargeted facial-image scraping, emotion recognition in workplace/education, etc.).
- **Article 6(1)** — safety component of / itself a product covered by Annex I EU harmonisation legislation requiring third-party conformity assessment → "high".
- **Article 6(2) + Annex III** — use in listed areas (biometrics, employment, education, healthcare, law enforcement, migration, critical infrastructure, etc.) → presumptively "high", *unless* Article 6(3) carve-out applies (narrow procedural task, no significant risk, not profiling natural persons).
- **Article 50** (transparency) — certain GPAI/synthetic-content duties → "limited".
- Everything else → "minimal".

**Why advisory-only is mandatory:**
- Misclassification has legal stakes — a user told "minimal" who is actually "high" skips conformity assessment and faces enforcement. That is precisely the kind of harm a governance tool must not cause.
- The Commission's **Draft Guidelines on classification of high-risk AI systems** (published 19 May 2026, Article 6(5) mandate) provide non-exhaustive practical examples — useful as few-shot grounding, but they are guidance, not a computable oracle. UNVERIFIED: the Digital Omnibus proposal may amend Article 6; ActReady must pin to a regulatory snapshot date and re-validate on change.
- **Disclaimer pattern (mirror permitpilot / "not legal advice" posture):** every classification result must render a banner: *"This is an automated, non-binding advisory based on the description you provided. It is not legal advice and does not constitute a conformity assessment. Confirm with qualified counsel and the Article 6(5) Commission guidelines before relying on any tier."* Plus a `REVIEW-COUNSEL` flag and a logged citation to the specific Article/Annex clause.

---

## 4. Eval / faithfulness — how we know the ML mappings are correct

We cannot ship assistive ML we cannot measure. Three layers:

1. **Golden set (offline, gated in CI).** A versioned corpus of (evidence_text → expected_control_ids) pairs curated by the team + an auditor advisor. Running the classifier against it yields precision/recall/F1 per control and overall coverage. Treat it like a pytest suite for the ML layer; block merges that drop recall below a threshold (e.g., <0.90).
2. **Human agreement (online).** Log every ML proposal and whether the human confirmed/overrode it. Track *override rate* per control and per model version. A rising override rate = model regression or drift in evidence distribution. This is the real-world eval the golden set can't capture.
3. **Control coverage recall.** Since governance cares about *missing* mappings (false negatives = unmet obligation), weight recall on control coverage heavily. A control with zero evidence mapped to it should never be silently "passed" by ML.

**Frameworks to adopt (don't reinvent):**
- **RAGAS** — `Faithfulness` / `ContextPrecision` / `ContextRecall` metrics measure whether generated/retrieved content is grounded in source (directly applicable to (a)/(b)/(d) grounding).
- **DeepEval** — pytest-style LLM eval; `HallucinationMetric`, faithfulness; integrates with CI and gives threshold assertions.
- **Giskard** — open-source ML testing/scanning for robustness, bias, and performance; good for the extraction schema.
- For drift (c), classical SPC math is sufficient; no LLM-judge needed (keeps it cheap and reproducible).

Faithfulness is the north star: every ML-generated mapping or sentence must be traceable to a source chunk + a logged model call. If it isn't traceable, it doesn't ship.

---

## 5. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Hallucination in a governance context** — confident wrong control mapping or fabricated citation | High | Citations mandatory; faithfulness eval (RAGAS/DeepEval); human confirmation gate; `REVIEW` flags on low confidence |
| **Vendor lock-in to one model provider** | Medium | `LLMProvider` abstraction + `ACTREADY_PROVIDER` flag; default off; open-weight/local (ollama) path always available |
| **Cost / latency at scale** | Medium | Embeddings run locally (bge/MiniLM); LLM calls only on explicit user action; cache embeddings; batch |
| **Reproducibility / non-determinism** | High | Log model + version + prompt + seed + raw I/O per call; deterministic engine stays source of truth; ML outputs are proposals, never state |
| **Regulatory drift** — AI Act amendments change classification basis | Medium | Pin regulatory snapshot date; re-validate classifier on change; version the control catalog |
| **Over-trust by user** — treats ML output as verdict | High | Disclaimers (§3); UI makes ML output visually distinct from confirmed state; audit log immutable |
| **Data sovereignty** — sending evidence to a third-party API | Medium | Local/default path; if cloud provider used, require explicit opt-in + DPA note; never send evidence off-box without flag |

**Architectural rule that contains all of them:** the deterministic engine remains the system of record. ML writes *proposals* into a separate, clearly-marked table; only a human action (or an explicit, logged automation rule the user defined) promotes a proposal to confirmed evidence state. The audit trail always shows proposal → human → confirmed.

---

## 6. Open questions (for planning phase)

1. **Threshold policy:** What is the minimum golden-set recall per control before the ML suggestion UI is enabled for that control? (Recommend ≥0.90, but needs team + auditor input.)
2. **Local-first vs. API:** Do design-partner deployments require a fully air-gapped path (ollama only), or is an opt-in API provider acceptable? Determines whether we invest in local model tuning first.
3. **Control-embedding index ownership:** Who curates the control index — us (prebuilt) or the user (their internal control framework)? Affects embedding schema and re-index cadence.
4. **Override-rate SLA:** What override rate triggers a model/version rollback? (Propose: sustained >15% on any control for 2 weeks.)
5. **Classification scope:** Do we ship the EU AI Act risk-tier advisor (§3) in v0.2, or defer to v0.3 given its legal exposure and the need for counsel-reviewed disclaimer copy?
6. **Drift signal source:** Which eval metrics will design partners actually stream into ActReady, and at what cadence, to make (c) meaningful rather than toy?
7. **Confidence calibration:** Do we need per-field confidence from the model, or is a heuristic (distance-to-nearest-control, reranker score) enough for v0.2?
8. **Audit-log immutability:** What storage guarantees (append-only, hash-chained) does the proposal log need to satisfy an ISO 42001 auditor?

---

## ML MVP SCOPE (recommendation for v0.2)

Ship ML **behind `ACTREADY_PROVIDER` (default off)** so the deterministic engine stays the default and the system of record. For v0.2, scope to the two lowest-risk, highest-leverage features:

1. **Evidence → control suggestion (§1a, §2).** Local embedding model (`bge-small-en-v1.5` or `all-MiniLM-L6-v2`) + `pgvector`/`Chroma`; curated control-embedding index; top-k suggestions with similarity scores; human confirms. No API key required.
2. **Structured field extraction from model cards / incident reports (§1b, §2).** `instructor` + Pydantic with field-level confidence; low-confidence → `REVIEW`. Local `ollama` model supported; cloud provider opt-in.

**Defer to v0.3:** EU AI Act risk-tier advisor (§3 — needs counsel-reviewed disclaimer + regulatory pinning), NL remediation/policy drafting (§1d — highest hallucination exposure), and ML-augmented drift prediction (§2c — classical SPC is enough for v0.2, and SPC ships in v0.2 as the drift detector).

**Always on, no flag:** deterministic mapping, freshness window, and classical SPC drift alerts (§2c) — these are not "ML features," they are core engine behavior and carry no hallucination risk.

---

### Sources
- EU AI Act, Regulation (EU) 2024/1689 — Articles 5, 6, 50; Annex III. EUR-Lex: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Article 6 classification rules: https://artificialintelligenceact.eu/article/6 ; EU AI Act Service Desk: https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6
- Draft Commission guidelines on classification of high-risk AI systems (19 May 2026, Art. 6(5)): https://digital-strategy.ec.europa.eu/en/library/draft-commission-guidelines-classification-high-risk-ai-systems
- Annex III high-risk areas: https://artificialintelligenceact.eu/annex/3/
- Model Cards for Model Reporting — Mitchell et al., 2019 (FAT* '19), arXiv:1810.03993. https://arxiv.org/abs/1810.03993
- sentence-transformers/all-MiniLM-L6-v2: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- BAAI/bge-small-en-v1.5 (MIT, 384-dim): https://huggingface.co/BAAI/bge-small-en-v1.5
- pgvector: https://github.com/pgvector/pgvector ; Chroma: https://www.trychroma.com
- instructor (structured outputs, Pydantic, 15+ providers incl. Ollama): https://python.useinstructor.com
- RAGAS: https://docs.ragas.io ; DeepEval: https://deepeval.com ; Giskard: https://www.giskard.ai
- Statistical Process Control / Western Electric rules: https://www.6sigma.us/six-sigma-in-focus/statistical-process-control-spc/
- "Not legal advice" disclaimer posture for AI legal tools: https://www.dentons.com/en/insights/newsletters/2023/august/7/practice-tips-for-lawyers/lessons-learned-from-ai-company-disclaimers

*Items marked UNVERIFIED are extrapolations pending confirmation with counsel or a regulatory snapshot.*
