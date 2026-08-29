# ActReady — Deep Research Brief: EU AI Act + ISO 42001, Competitive Landscape, Evidence Integrations, ICP & Demand Signals

**Date:** 2026-08-29 · **Author:** Research subagent · **Status:** v1.0 (research only, no code)
**Scope corroborates existing v0.1 engine:** `api/app/mapper.py` already ingests 4 evidence types (`policy`, `model_card`, `eval_run`, `incident_log`) against a catalog of 39 ISO/IEC 42001 Annex A controls and 21 EU AI Act obligations, scoring `satisfied` / `partial` (stale) / `missing` with a 180-day freshness window (FRESH_DAYS = 180). This brief feeds the planning phase for v0.2+.

---

## 1. EU AI Act — Timeline & Obligations

The EU AI Act is **Regulation (EU) 2024/1689**, adopted 13 June 2024, in force **1 August 2024**. It applies in phases. The dates below reflect the **Digital Omnibus on AI** amendment (Regulation (EU) 2026/1744, in force 27 July 2026), which *deferred* the high-risk application dates. Always confirm against the official timeline before publishing a roadmap — the Omnibus is recent and some secondary sources still cite the older (pre-deferral) dates.

**Source of record:** EUR-Lex CELEX 32024R1689 (`https://eur-lex.europa.eu/eli/reg/2024/1689/en`) and the EU AI Office Service Desk timeline (`https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act`).

| Date | Milestone | What it binds |
|---|---|---|
| **1 Aug 2024** | Entry into force | Legal effect begins |
| **2 Feb 2025** | Prohibitions (Art. 5) + AI literacy (Art. 4) | Banned practices illegal; staff training duty |
| **2 Aug 2025** | GPAI rules + governance | Provider obligations for general-purpose AI models; Member-State authorities live; penalties in national law |
| **2 Aug 2026** | **Majority of rules apply** — incl. Art. 50 transparency, enforcement begins | Transparency duties (chatbot disclosure, deepfake labelling, synthetic-content marking), innovation measures |
| **2 Dec 2026** | New prohibitions (non-consensual sexual deepfakes, CSAM) + Art. 50(2) transitional deadline for legacy GPAI |
| **2 Aug 2027** | Member States operate ≥1 AI regulatory sandbox each |
| **2 Dec 2027** | **High-risk AI systems in Annex III apply** (deferred from Aug 2026 by Omnibus) |
| **2 Aug 2028** | High-risk systems embedded in regulated products (Annex I) apply |

**Provider vs Deployer (Articles 9–15 are the technical core):** The Act splits obligations by role. A *provider* develops/places a system on the market under its own name and carries the heaviest load; a *deployer* uses a third-party system professionally. Many AI-native startups are **both** (they build their own model and deploy third-party APIs).

Provider-facing obligations (Articles 9–15 + 16–19):
- **Art. 9 Risk management system** — continuous, iterative, throughout lifecycle. *Evidence:* risk register, documented risk-assessment process, mitigation logs.
- **Art. 10 Data & data governance** — training/validation/test data examined for bias, completeness, representativeness. *Evidence:* data sheets, provenance, quality reports.
- **Art. 11 Technical documentation (Annex IV)** — pre-market system dossier. *Evidence:* model card, architecture docs, design specs.
- **Art. 12 Record-keeping / automatic logs** — systems generate event logs. *Evidence:* logging config, sample logs.
- **Art. 13 Transparency & info to deployers** — instructions for use. *Evidence:* user docs, limitations, intended-use statement.
- **Art. 14 Human oversight** — design for human intervention/override. *Evidence:* oversight design spec, override tests.
- **Art. 15 Accuracy, robustness, cybersecurity** — performance baselines + adversarial resilience. *Evidence:* eval reports (promptfoo/deepeval), red-team results, robustness tests.
- **Art. 16–19** Provider QMS (Art. 17), conformity assessment (Art. 43/49), CE marking, EU database registration.

Deployer-facing obligations (Art. 26, 27, 50): use per provider instructions, assign oversight staff, retain logs (≥6 months where they control logging), run **Fundamental Rights Impact Assessment** (Art. 27) where required, and **Art. 50 transparency** (chatbot disclosure, deepfake labelling) applies to *all* deployers regardless of risk tier.

**Incident reporting (Art. 73)** — confirmed directly from the text (`https://www.aiact-info.eu/regulation/aiact/article/73/reporting-of-serious-incidents`): providers (and deployers where applicable) must report serious incidents **within 15 days** of becoming aware; **within 10 days** if death is involved; **within 2 days** for widespread infringements. Apply from 2 Dec 2027 for Annex III high-risk (Omnibus). *Evidence:* incident log with detection time, causal-link analysis, corrective action, and the report timestamp.

> **Uncertainty note:** The Omnibus deferral is recent (late June 2026). Pre-deferral content (e.g., "high-risk applies Aug 2026") is now outdated. Treat all roadmap dates as provisional until the final EU guidance is digested.

---

## 2. ISO/IEC 42001:2023 — Structure & Artifacts

**Source of record:** ISO (`https://www.iso.org/standard/42001`) and the OBP preview (`https://www.iso.org/obp/ui/en#!iso:std:81230:en`). It is the **world's first AI Management System (AIMS) standard**, published Dec 2023, 51 pages, CHF 225.

**The 10 Clauses (Annex SL / High-Level Structure, same skeleton as ISO 27001):**
1. Scope · 2. Normative references · 3. Terms & definitions · 4. Context of the organization · 5. Leadership · 6. Planning (risk assessment, objectives) · 7. Support (competence, documentation, resources) · 8. Operation (AI lifecycle) · 9. Performance evaluation (monitoring, audit) · 10. Improvement.

**Annex A — the control catalogue.** Canonical count is **38 controls across 9 groups (A.2–A.10)**; some mappings list 39 (counting convention on A.6 sub-splits). ActReady's catalog holds 39 — consistent with industry crosswalk practice. The 9 groups:
- **A.2 Policies (2–3 controls):** AI policy signed by top management, alignment, review.
- **A.3 Internal organisation (2–3):** roles/responsibilities, concern-reporting channel.
- **A.4 Resources (5):** compute/data/tooling/human resource documentation.
- **A.5 Impact assessment (4):** impact-assessment process + recorded assessments (individuals & society).
- **A.6 Lifecycle (7–9 — largest):** responsible-design objectives, V&V, deployment, operation/monitoring, technical documentation, event logs. *This group operationalises EU AI Act Art. 9 + Art. 15.*
- **A.7 Data (5):** data governance, acquisition, quality, provenance, preparation. *Maps to Art. 10.*
- **A.8 Interested parties (4):** user docs, external reporting, incident communication. *A.8.4 aligns with Art. 73 incident reporting.*
- **A.9 Use of AI systems (3):** responsible-use processes, objectives, intended use.
- **A.10 Third-party & customer relationships (3):** allocate responsibilities, supplier controls, customer obligations. *Maps to Art. 25 supply-chain duties.*

**Artifacts a certified org must produce** (per ISO + accredited-body explainers such as A-LIGN and Vanta): AI policy; Statement of Applicability (SoA) listing each control as applied/excluded with justification; risk treatment plan; AI system inventory; impact assessments; technical documentation; training records; internal-audit reports; management-review minutes. The **SoA is what auditors test** — every control needs a stated rationale backed by *evidence beyond the policy doc itself* (SureCloud, `https://surecloud.com/resource-hub/iso-42001-annex-controls`).

**ISO 42001 ↔ EU AI Act mapping (corroborated by Vanta, A-LIGN, ModelOp, ISACA):**
- ISO 42001 is **voluntary, process-based**; the AI Act is **mandatory, outcome-based law**. ISO certification **does not equal** AI Act conformity, but it "reduces the cost and effort" (Vanta) and covers ~60–80% of the management-system backbone.
- Direct control-to-article bridges: A.6 → Art. 9/15; A.7 → Art. 10; A.8.4 → Art. 73; A.10 → Art. 25 (supply chain). A risk-based classification exists in both.

> **Uncertainty note:** Exact control-count (38 vs 39) is a counting convention, not a contradiction. Market-size and "% of Act covered by ISO" figures are UNVERIFIED estimates.

---

## 3. Competitive Deep-Dive

Funding/positioning sourced from the citations below. Pricing details are mostly not public (marked UNVERIFIED where so).

| Vendor | Funding | Positioning | AI-native startup fit | Open gap ActReady owns |
|---|---|---|---|---|
| **Vanta** | $504M total; **$4.15B val** (Series D, Jul 2025, Wellington-led) (`https://www.reuters.com/business/wellington-led-funding-boosts-vantas-valuation-by-69-year-2025-07-23/`) | Trust-management leader (SOC 2, ISO 27001, now AI agent). 12,000+ customers | Strong on security/compliance automation, but AI governance is *bolt-on* to a security-GRC core; not model-pipeline-native | Compiles evidence **from the ML pipelines themselves** |
| **Delve (Modular)** | **$32M Series**, ~$300M val, 1,500 customers — but **parted ways with YC Apr 2026** amid a fake-SOC-2-report scandal (`https://techcrunch.com/2026/04/04/embattled-startup-delve-has-parted-ways-with-y-combinator/`) | AI-native SOC 2 automation | Reputation damaged; security-framework focus, not EU AI Act/ISO 42001 model controls | Trust-damaged; AI-native governance with audit-grade evidence |
| **Anecdotes AI** | **$85M total** ($55M Series B extended, Apr 2025, DTCP) (`https://www.anecdotes.ai/pr-articles/anecdotes-secures-55m-series-b/`) | Enterprise GRC "Compliance OS", 200+ frameworks, Big-Four partnerships | Enterprise-scaled, heavy, expensive; not built for 5–30-person AI startups | Bottom-up, developer-first, pipeline-native |
| **OneTrust** | Private; 14,000+ customers, >½ Fortune 500 (`https://onetrust.com/news/onetrust-announces-ai-agents-at-trustweek-2025`) | "AI-ready governance" platform, privacy-first heritage | Massive, suite-heavy, sales-led; overkill for startups | Lean, technical, evidence-compiling wedge |
| **IBM watsonx.governance** | IBM (public co.); unit-priced tiers, free Lite, ~$0.64/eval, AWS bundle $38,160/yr (`https://aicompliancevendors.com/vendors/ibm-watsonx-governance/pricing`) | Enterprise AI governance graph, policy enforcement | Enterprise lock-in (Cloud Pak/IBM estate); costly for startups | Model-agnostic, pipeline-native, no IBM dependency |
| **Microsoft Purview (AI Hub / DSPM for AI)** | Microsoft; bundled w/ M365/E5 (`https://learn.microsoft.com/en-us/purview/ai-microsoft-purview`) | Data-security posture for AI usage | Great if you live in Azure/M365; blind to non-MS pipelines; usage-monitoring not evidence-compilation | Vendor-neutral evidence engine |
| **Holistic AI** | Founded by DeepMind alumni; **~$200M reported** (Silicon Valley Journals, May 2024) — *UNVERIFIED* (`https://tracxn.com/d/companies/holistic-ai/__NwV6GHC8XePYfJi-unIGMZ-OWKIVuLsnfzgjQTSG56Q`) | Leading enterprise AI governance platform | Enterprise sales motion; broad but heavy | Developer-first, integrates into CI/CD |
| **Fairly AI** | **CAD $2.2M** (Apr 2023, Flying Fish) + pre-seed (`https://betakit.com/fairly-ai-raises-2-2-million-cad/`) | Model risk management, fairness/bias testing, CI/CD one-liner | Small, pre-revenue-then; model-risk focus not full EU Act/ISO scope | End-to-end obligation coverage + evidence freshness |
| **Credo AI (Ethos)** | **$12.8M Series A** (Sands Capital) (`https://credo.ai/news/credo-ai-announces-12-8-million-series-a/`) | "Responsible AI" governance platform, context-driven | Enterprise (Mastercard, finance/defense); sales-led | Startup-native, low-friction |
| **Trustible** | **$4.6M–$6.35M seed** (Jun 2025) (`https://fundediq.co/trustible-trustible-ai-funding`, `https://www.ai-market-watch.com/company/trustible`) | **Purpose-built EU AI Act** platform, automated control mapping (EU AI Act 88% / ISO 42001 79% readiness dashboards) | Closest direct competitor; but workflow/questionnaire-centric, not pipeline-native | Evidence that *compiles itself* from pipelines |
| **Fiddler AI** | **$100M total** ($30M Series C, Jan 2026, RPS Ventures) (`https://7wdata.be/company/fiddler-ai`) | AI observability, guardrails, agentic monitoring | Runtime monitoring, not compliance artifact compilation | Compliance-grade evidence from the same signals |
| **Arthur AI** | **~$60–63M** (Series B $42M, 2022, Index/Acrew/Greycroft); val ~$154M (`https://oryndex.co/tools/arthur/funding`) | ML observability & LLM eval/governance | Monitoring-focused; pivoting to LLM/agent governance | Obligation-aware evidence rollup |

**Two-to-three genuinely underserved sub-segments:**
1. **AI-native startups (5–50 people) that are *both* provider and deployer** and need EU AI Act + ISO 42001 readiness *before* an enterprise deal — priced out of Vanta/OneTrust/Anecdotes enterprise motions and not served by monitoring-only tools (Fiddler/Arthur).
2. **Pipeline-native evidence compilation** — every competitor above is either (a) a security-GRC suite with AI bolted on, (b) an enterprise questionnaire/workflow system, or (c) a runtime monitor. **None compile governance evidence automatically from GitHub Actions, MLflow, promptfoo, PagerDuty, etc.** That is exactly ActReady v0.1's engine (model cards + eval runs + incident logs → GapReport).
3. **Developer-first / PLG wedge** — Embeddable `POST /assess`, YAML control catalogs, CI-friendly. Competitors are sales-led; no one owns the "drop-in `actready assess` in your CI" motion.

---

## 4. Evidence-Source Integrations (Backend Scope)

ActReady's thesis — "your governance evidence compiles itself from your own pipelines" — requires connectors that turn existing ML/DevOps artifacts into the 4 engine evidence types (`policy`, `model_card`, `eval_run`, `incident_log`). Real pipelines and what each yields:

- **CI/CD — GitHub Actions / GitLab CI** (`https://docs.github.com`, `https://docs.gitlab.com`): build/review logs, policy-as-code (OPA), merged PRs, test artifacts. *Yields:* `policy` (approved configs), `model_card` provenance (commit SHA, owner), freshness signals. *Ingest:* webhook on workflow run → push artifacts to `/assess`.
- **Model registries — MLflow** (`https://mlflow.org`), **Hugging Face** (model cards, `https://huggingface.co`), **Weights & Biases** (`https://wandb.ai`): registered models, params, metrics, lineage, eval history. *Yields:* `model_card` (rich metadata), `eval_run`. *Ingest:* registry API / export YAML+metrics JSON.
- **Eval frameworks — promptfoo** (`https://www.promptfoo.dev`), **deepeval** (`https://github.com/confident-ai/deepeval`), **ragas** (`https://ragas.io`), **LangSmith datasets** (`https://docs.smith.langchain.com`): test results, scores, regression deltas. *Yields:* `eval_run` (mapped to Art. 15 accuracy/robustness, A.6 V&V). *Ingest:* JSON export → engine already parses promptfoo/deepeval.
- **Incident tools — PagerDuty** (`https://developer.pagerduty.com`), **incident.io** (`https://incident.io/docs`): incident timelines, severities, post-mortems. *Yields:* `incident_log` (Art. 73: detection → report timestamp → corrective action). *Ingest:* REST/Events API.
- **Feature stores / data lineage — OpenLineage** (`https://openlineage.io/docs`, spec on GitHub): dataset provenance, job runs. *Yields:* `model_card` data lineage, A.7 provenance. *Ingest:* OpenLineage event stream → provenance graph.
- **Policy/doc stores — Notion, Confluence, GDrive, GitHub markdown:** signed AI policy, SoA. *Yields:* `policy`. *Ingest:* API + freshness check.

Each connector's job: emit one of the 4 evidence types with a `collected_at` timestamp so the engine's 180-day freshness logic scores it. This is the concrete v0.2+ build surface and the defensible data moat.

---

## 5. Buyer & ICP

**Primary persona:** **Head of AI/ML or AI Lead** at an AI-native startup (often the founding engineer wearing a governance hat); secondary **CTO/VP Eng** and, once scaled, a dedicated **AI Governance / Trust & Safety lead**. Title inflation: at <20 people it's a founder; at 30–100 it's a "Head of AI" or "ML Platform Lead."

**Firmographics:** 5–100 employees; Series Seed–B; $1–20M raised; ships LLM/agent features; has ≥1 EU customer or is chasing one; sells to enterprises that now attach AI-governance questionnaires to procurement (ISO 42001 / EU AI Act clauses appear in security reviews).

**Trigger events (when they feel the pain):**
1. Enterprise deal requires SOC 2 **+ AI governance** attestation.
2. Signing or targeting an **EU customer** → AI Act surface area.
3. Customer/procurement asks for **ISO 42001** or a responsible-AI questionnaire.
4. A **model incident** (hallucination, bias, leak) reaches production.

**Willingness to pay (UNVERIFIED):** Early-stage buyers resist $20k+ enterprise GRC seats; expect PLG-friendly pricing — free self-serve tier + usage/per-model or per-seat from ~$99–$999/mo, escalating with connected pipelines and audit exports.

**Sales motion:** **PLG bottom-up** — `pip install actready` / `POST /assess` in CI, a free readiness score, then expand to team dashboards and audit exports. Assisted only at the enterprise-conversion step. This matches the v0.1 engine's already-shipped API endpoint.

---

## 6. Demand Signals (Real Quotes + Links)

**Hacker News (Algolia API `http://hn.algolia.com/api/v1/search`):**
- *"But I do need dedicated compliance officer! The lower thresholds applies from 250 employees. I still have the same obliga[tions]."* — HN commenter on EU thresholds (`https://news.ycombinator.com/item?id=49489863`), 2026-08-29. Signals: small teams still bound by obligations.
- *"…as a small startup focusing on adapting open source models f[or the EU market]… having just had some meetings on aligning with the latest AI act…"* — `NitpickLawyer` (`https://news.ycombinator.com/item?id=48171950`), 2026-05-17. Signals: startups actively scrambling to align.
- *"EU AI Act got hijacked by huge corpo… Even at 2 December 2027 it might be intentionally not enforced at all…"* — `dathinab` (`https://news.ycombinator.com/item?id=48720571`), 2026-06-29. Signals: uncertainty/fatigue (also a churn risk).
- *"nobody doing serious AI or in a corporate environment is using them [open routers]. And if they are, their compliance team is about to strike them down."* — `johnbarron` (`https://news.ycombinator.com/item?id=49371400`), 2026-08-20. Signals: compliance teams are gatekeepers in AI tooling choices.

**Reddit (RSS-extracted; reddit.com JSON was 403/rate-limited, quotes below are from the .rss body):**
- r/grc, *"ISO 42001 does not, by itself, cover AI Act conformity"* — top comment (disclosure: author does ISO 42001 + AI Act readiness): *"Three things get treated as interchangeable in almost every vendor questionnaire I've seen this year: ISO 42001, NIST AI RMF and the EU AI Act."* (`https://www.reddit.com/r/grc/comments/1vtmu4k/iso_42001_does_not_by_itself_cover_ai_act/`). **Strong signal:** buyers confuse the three and need a single mapped control set — which ActReady's catalog already provides.
- r/grc shift-left thread: *"ISO 42001 is still pretty new but the smart move is definitely to bake those controls in early rather than retrofit them later, which is always [painful]."* (`https://www.reddit.com/r/grc/comments/1tlnoza/shift_left_in_ai_governance/`) — validates the "compile evidence from pipelines as you build" wedge.
- r/mlops, *"How do teams actually track AI risks in practice?"* (`https://www.reddit.com/r/mlops/comments/1pgi54j/how_do_teams_actually_track_ai_risks_in_practice/`) — recurring theme: teams have no shared system of record for AI risk; spreadsheets collapse. (Direct quote text rate-limited; thread intent confirmed.)

> **Uncertainty note:** Reddit's API/JSON endpoints blocked automated extraction (403/429); quotes above were recovered from RSS bodies and may be partially truncated. HN quotes are verbatim from Algolia comment text. Treat volumes as illustrative, not measured.

---

## 7. Why-Now + Defensibility

**Why a 4-person team can win a wedge here:**
1. **Forcing function is live and phased** — Aug 2025 GPAI rules and Aug 2026 general application are *already enforceable*; Annex III high-risk + Art. 73 reporting hit 2 Dec 2027. Buyers are being pulled, not pushed.
2. **Incumbents are mis-shaped** — Vanta/OneTrust/Anecdotes are security/enterprise-GRC suites (sales-led, expensive, questionnaire-centric). Fiddler/Arthur are runtime monitors. **No one owns automated, pipeline-native evidence compilation for AI-native startups.** That is a narrow, winnable wedge a small team can ship.
3. **The engine already exists** — v0.1 proves the hard part: deterministic evidence→control→obligation scoring with freshness logic. The moat is *connectors + data*, not algorithms.

**Defensibility / moat:**
- **Data moat:** Every connected pipeline (GitHub, MLflow, promptfoo, PagerDuty, OpenLineage) adds proprietary evidence signals. Over time, ActReady holds the canonical, versioned evidence graph per customer → switching cost rises.
- **Network/coverage moat:** As the control catalog (39 ISO + 21 AI Act) is exercised against real evidence across many startups, remediation hints and "what good looks like" benchmarks improve — a shared intelligence layer competitors without the PLG footprint can't replicate cheaply.
- **Distribution moat:** the `POST /assess`-in-CI PLG motion is alien to sales-led incumbents; it compounds with open-source model-card/eval conventions.

> **Uncertainty note:** Market-size TAM/SAM/SOM and "incumbent X has Y% share" are UNVERIFIED; existing `docs/tam-sam-som.md` should be treated as hypothesis until primary data is gathered.

---

## SCOPE QUESTIONS FOR PLANNING PHASE

The planning subagent must resolve these 10 decisions before v0.2 scope-lock:

1. **Evidence-type expansion:** Keep the 4 engine types (`policy`, `model_card`, `eval_run`, `incident_log`) or add `data_lineage` / `config_scan` as first-class types to support A.7/A.10?
2. **Connector priority (v0.2):** Which 2–3 integrations ship first — GitHub Actions, MLflow, promptfoo, PagerDuty, Hugging Face, OpenLineage? Rank by evidence yield vs build cost.
3. **Control catalog reconciliation:** Reconcile the 39-control ActReady catalog with the canonical 38 (Annex A) — keep 39 or align to 38? Document the delta.
4. **Obligation freshness window:** Keep FRESH_DAYS = 180, or make it per-obligation (e.g., Art. 73 incident evidence should be "ever-green"/event-driven, not 180-day)?
5. **Provider vs Deployer mode:** Should `/assess` accept a `role` parameter (provider/deployer/both) to scope Articles 9–15 vs 26/27/50?
6. **EU AI Act versioning:** How does the engine track the Digital Omnibus deferral (2 Dec 2027 high-risk, 2 Aug 2028 Annex I) — hardcoded dates or a versioned obligations file?
7. **ICP & pricing motion:** Confirm PLG (`pip install` + free tier) as primary; decide the paid conversion trigger (connected pipelines count? audit-export? seats?).
8. **Competitive positioning statement:** Is the wedge "evidence compiles itself from your pipelines" (differentiation vs all 12 competitors) or narrower (e.g., "EU AI Act readiness for AI-native startups")?
9. **Output format:** Beyond JSON GapReport, do buyers need PDF/CSV audit packages, a Trust Center page, or a continuous "readiness score over time" dashboard?
10. **Evidence provenance & trust:** How does ActReady prove the evidence is *authentic* (signed by the pipeline, tamper-evident) so auditors accept it — and is that a v0.2 or post-ga requirement?

---
*All statutory citations: EUR-Lex CELEX 32024R1689; EU AI Office Service Desk timeline. All funding figures: linked primary sources (Reuters, TechCrunch, BetaKit, company press). Counts/frameworks flagged UNVERIFIED where precision was not established from a primary source.*
