# ActReady — Product Strategy & v0.2 Milestone Plan

**Author:** Product/Planning lead agent · **Date:** 2026-08-29 · **Status:** v0.2 plan (planning)
**Inputs:** `research-deep-dive.md`, `backend-research.md`, `frontend-research.md`, `ml-research.md` (all in `docs/`).
**Note on domain plans:** At write time, `docs/planning/ml-plan.md` **is present** (21 tickets, A1–G2) and its scope is folded into the **ML-Assist** epic in §7. `backend-plan.md` and `frontend-plan.md` are **not yet present**, so the Foundations / Auth / Integrations / Reporting / Frontend epics in §7 are rolled up from those briefs' *MVP-scope* sections (backend §6, frontend §6) plus cross-cutting items from `research-deep-dive.md` §7. When all three domain plans land, re-cast their ticket IDs into the six epic buckets below — the structure is designed to absorb them verbatim.

---

## 1. Positioning Reframed

**One sentence:** *ActReady turns the ML pipelines AI-native startups already run into auditor-traceable EU AI Act + ISO 42001 readiness — without a single compliance questionnaire.*

**The wedge.** Every incumbent — Vanta, OneTrust, Anecdotes, Holistic AI, Trustible, Fiddler, Arthur — falls into one of three mis-shaped buckets: a security/enterprise-GRC suite with AI bolted on, a runtime monitor, or a questionnaire/workflow engine (`research-deep-dive.md` §3). **None of them compile governance evidence automatically from the artifacts a team already produces** — GitHub Actions, MLflow, promptfoo/deepeval, PagerDuty. That is the confirmed gap, and it is exactly what ActReady v0.1's deterministic engine already does: it ingests `policy`, `model_card`, `eval_run`, and `incident_log` and derives control status from those artifacts, not from a human filling out a form.

The differentiation is structural, not cosmetic: competitors *assert* control status (Trustible scores controls; Delve was caught auto-asserting passing evidence — `frontend-research.md` §2); ActReady *derives* it from dated, hash-chained, source-linked evidence. That makes the output defensible to a regulator and immune to the Delve-style independence failure.

**Why now.** The forcing function is live and phased, and the timeline just got more forgiving in the team's favor. The **Digital Omnibus (Regulation (EU) 2026/1744)** deferred Annex III high-risk obligations and Article 73 incident reporting from August 2026 to **2 December 2027** (`research-deep-dive.md` §1). That deferral is the gift: buyers are *pulled* toward readiness now (GPAI rules already enforceable since Aug 2025, general application since Aug 2026) but have a clear, concrete 2-Dec-2027 cliff to prepare against. A 4-person team can own the "get ready before the cliff" wedge while incumbents are still selling year-long enterprise deployments. Supporting demand signals: HN commenters confirm small teams are still bound by obligations and *compliance teams gatekeep AI-tooling choices*; r/grc confirms buyers conflate ISO 42001 / NIST AI RMF / EU AI Act and want one mapped control set — which ActReady's 39-control + 21-obligation catalog already provides (`research-deep-dive.md` §6).

---

## 2. v0.2 Theme

**A startup can connect its ML pipeline and see a live, auditor-traceable readiness score in under one hour — no sales call, no questionnaire.**

This is the single outcome that the whole release is judged against. Everything in v0.2 either reduces time-to-first-score, increases the trustworthiness of that score, or proves the score is reproducible for an auditor. If a feature doesn't serve that sentence, it is cut (see §4). The headline activation target is `<1 hour signup → first score`, deliberately tighter than Trustible's "live in 90 days" and Delve's TurboTax narrative — because we are PLG and self-serve, not sales-led (`frontend-research.md` §4, Flow A).

---

## 3. Milestone Sequence

For a 4-person team (2 backend, 1 frontend, 1 ML/full-stack) over roughly **14 weeks**, sequenced so each milestone is independently shippable and demoable.

### M1 — Auth + DB + engine-multitenant
- **Goal:** Convert the stateless v0.1 CLI into a tenant-aware service without touching the deterministic engine.
- **Ships:** FastAPI + PyJWT `get_principal` (auth seam kept thin so WorkOS/Clerk can swap in later, `backend-research.md` §1.1); Postgres + SQLAlchemy 2.0/Alembic; **Row-Level Security** tenant isolation via transaction-local GUCs (`backend-research.md` §1.2); `tenants / users / memberships / invites` tables; engine wrapped behind a tenant-scoped service layer.
- **Exit criteria:** Two isolated tenants cannot read each other's data even if app code omits a filter; `POST /assess` runs under a tenant context and writes to a scoped store.
- **Timeline:** Weeks 1–4.

### M2 — First 2 integrations + live scorecard
- **Goal:** Evidence flows in automatically and the hero number appears in a web UI.
- **Ships:** **GitHub App** adapter (webhook + poll for eval artifacts, HMAC-verified, `backend-research.md` §2) and **promptfoo/deepeval via CI push** (reuses existing parser exactly); immutable `evidence_artifacts` + `control_mappings` + `ingestion_runs` tables; per-source `try/except` error isolation so one flaky source never 422s the assessment (`backend-research.md` §5); frontend **Readiness Scorecard**, **Control Library**, and **Per-Control Detail Drawer** (`frontend-research.md` §6 P0).
- **Exit criteria:** A user connects a GitHub repo (or uploads an eval JSON), is auto-redirected to a scorecard with a computed % and worst-first gaps in <5 min; a deliberately broken token degrades one source without killing the report.
- **Timeline:** Weeks 4–9.

### M3 — Report export + share link
- **Goal:** Output an auditor-acceptable, shareable, reproducible artifact.
- **Ships:** Deterministic HTML→PDF via WeasyPrint (`backend-research.md` §4); versioned `report_snapshots` pinned to catalog version; signed, time-limited read-only **share link** (Flow C, `frontend-research.md` §4); minimal **Audit/Export View** (Markdown + JSON; PDF via server render).
- **Exit criteria:** A report generated today reproduces byte-identically from stored evidence next week; an external party with a share link sees the scorecard + linked evidence with no tenant credentials.
- **Timeline:** Weeks 9–12.

### M4 — ML suggestion/extraction behind flag
- **Goal:** Assist, never decide — prove the ML layer adds leverage without becoming a liability.
- **Ships (both gated behind `ACTREADY_PROVIDER`, default off, `ml-research.md` §0/§6):** (a) **Evidence→control suggestion** — local embedding (`bge-small-en-v1.5` / `all-MiniLM-L6-v2`) + `pgvector`/`Chroma`, curated control index, top-k with similarity scores, human confirms; (b) **structured field extraction** from model cards/incident reports — `instructor` + Pydantic, field-level confidence, low-confidence → `REVIEW`. Always-on, no-flag: deterministic mapping, freshness window, and classical **SPC drift alerts** (`ml-research.md` §2c).
- **Exit criteria:** Golden-set recall ≥0.90 per control before the suggestion UI is enabled for that control; every proposal is logged (model/version/prompt/raw I/O) and never auto-promotes to confirmed state without a human action.
- **Timeline:** Weeks 12–14 (parallelizable with M3's tail).

---

## 4. Scope Trade-Offs — What We Explicitly DO NOT Build in v0.2

| Deferred | Why it's out |
|---|---|
| **Enterprise SSO (WorkOS/Clerk)** | ICP is 5–100-person AI-native startups; SSO is an enterprise-conversion add-on, not an activation blocker. We keep the `get_principal` seam and adopt WorkOS *when the first SSO deal appears* (`backend-research.md` §1.1). |
| **Stripe billing** | PLG free tier + usage expansion is the motion; monetization is post-traction. Billing UI is pure distraction in v0.2. Pricing flag in the data model is enough to gate features conceptually (`backend-research.md` §1.4). |
| **Temporal** | Durable multi-step ingestion is over-engineering for two connectors. ARQ (or a thin job interface) ships v0.2; Temporal is the documented upgrade path (`backend-research.md` §1.5). |
| **Runtime / production monitoring** | That's Fiddler/Arthur's lane and a different buyer conversation. ActReady is an evidence *compiler*, not an observability daemon — the frontend brief explicitly rejects the "always-on dashboard you live in" framing (`frontend-research.md` §0). |
| **Policy / Playbook generator** | Highest hallucination exposure (drafted policy cited to an auditor as authoritative, `ml-research.md` §1d) and not needed for the <1-hour-score outcome. Deferred to v0.3+ (`frontend-research.md` §1g). |

We also hold **ML risk-tier advisory** (EU AI Act classifier) and **NL remediation drafting** to v0.3 — both carry legal-exposure and counsel-review requirements that v0.2's PLG motion doesn't need (`ml-research.md` §3, §6).

---

## 5. Metrics

| Metric | Definition | v0.2 Target |
|---|---|---|
| **Activation — time-to-first-score** | Median minutes from signup to first computed readiness % | < 60 min (Flow A `<5 min` best-case) |
| **Retention — weekly re-assessment rate** | % of activated tenants that trigger ≥1 new `report_snapshot` per week | ≥ 30% by week 8 post-launch |
| **Evidence-source connected** | Median distinct sources (GitHub / CI-eval / upload) linked per active tenant | ≥ 2 |
| **ML suggestion acceptance rate** | (human-confirmed proposals) / (total proposals shown), per control | ≥ 0.70 where enabled; **guardrail:** override rate >15% on any control for 2 weeks → rollback (`ml-research.md` §6 Q4) |

Supporting: per-source ingestion success ≥99%; report reproducibility = 100% (byte-identical re-render from stored artifacts).

---

## 6. Go-To-Market

**Motion: PLG bottom-up.** `pip install actready` / `POST /assess` in CI → free readiness score → expand to team dashboards and audit exports (`research-deep-dive.md` §5). The `POST /assess`-in-CI wedge is alien to every sales-led incumbent and compounds with open-source model-card/eval conventions — a distribution moat they can't cheaply copy (`research-deep-dive.md` §7).

**Channels:**
1. **Developer communities** — HN, r/mlops, r/grc, LLM-eng Slack/Discords. Seed with "drop-in `actready assess` in your CI" and the free score. The r/mlops "how do teams track AI risk?" thread shows the pain is top-of-mind (`research-deep-dive.md` §6).
2. **ISO 42001 auditors as a channel** — auditors are the trust arbiters and repeatedly see buyers conflate ISO 42001 / NIST / EU AI Act. Equip them with the share-link + evidence-vault view so they *recommend* ActReady to auditees (Vanta's "auditors examine source data, no screenshots" pattern, `frontend-research.md` §2). This is a two-sided pull: auditees come pre-qualified.
3. **Trigger events** (outbound + lifecycle nudges): enterprise deal requiring SOC 2 + AI-governance attestation; signing/targeting an EU customer; procurement asking for ISO 42001; a model incident reaching production (`research-deep-dive.md` §5).

**Pricing posture:** free self-serve tier (watermarked summary) + usage/per-model or per-seat from ~$99–$999/mo escalating with connected pipelines and audit exports (`research-deep-dive.md` §5). No enterprise list price in v0.2.

**Kill criteria (from earlier research):** **< 3 paid pilots in 90 days** → pause paid motion, return to free-tier activation loop and re-examine ICP. Secondary guardrail: activation > 60 min median for two consecutive weeks → the <1-hour theme is broken and M2/M3 need repair before GTM spend.

---

## 7. Unified Issue Rollup (Prioritized Backlog)

**All three domain plans are now present** (`backend-plan.md` = 22 tickets E1.1–E6.3; `frontend-plan.md` = 25+ tickets A1–H4; `ml-plan.md` = 21 tickets A1–G2). This rollup reconciles their real tickets into six epics, mapping each plan's IDs so the parent agent can trace any line item back to source. Priority = activation leverage.

> **Scope conflict to ratify (flagged, not silently resolved):** the backend plan ACCEPTS **WeasyPrint HTML→PDF export in v0.2** (E4.1) and lists RPT-1 as in-scope, while the frontend plan **DEFERS the PDF *UI*** to P1/v0.3 (FR §5 Q6, H4) — Markdown + JSON only ship in the P0 Export view. Resolution: the **PDF generation capability exists in v0.2 (backend)** but is exposed only via a server endpoint, not a primary UI button, until the frontend P1 lands. This is a deliberate capability-vs-UI split, not a contradiction — both plans agree PDF is not a blocking P0 surface. Product ratifies: ship backend PDF (`GET /api/report?format=pdf`) in v0.2; gate the UI button behind the P1 frontend ticket H4.

### Epic: Foundations (FOUND)
- **FOUND-1** Postgres + SQLAlchemy 2.0 + Alembic baseline (`alembic upgrade head` on fresh PG). → *backend E1.2*
- **FOUND-2** RLS tenant isolation: `app_owner`/`app_user` roles, `SET LOCAL app.tenant_id` GUC, `ENABLE`+`FORCE ROW LEVEL SECURITY` (applied in a dedicated `enable_rls` migration per backend §2). → *backend E1.3*
- **FOUND-3** Immutable `evidence_artifacts` (DB trigger blocks UPDATE/DELETE) + sha256 content-hash + `/verify` recompute. → *backend E2.1*
- **FOUND-4** Versioned `report_snapshots` pinned to `catalog_version` + `manifest_hash` chaining (Omnibus dates as data, no hardcoded law dates). → *backend E2.3, E6.3*

### Epic: Auth + Multi-tenant (AUTH)
- **AUTH-1** FastAPI + PyJWT `get_principal` dependency (sub/tenant_id/exp; no secrets in token). → *backend E1.1*
- **AUTH-2** Org/User/Membership schema + signup (table named `organizations`; `viewer` role reserved for v0.4 auditor). → *backend E1.4*
- **AUTH-3** Frontend auth + workspace shell (login/register, protected routes, sidebar, Zustand token store). → *frontend A1–A4, B1–B3*

### Epic: Integrations (INT)
- **INT-1** GitHub App adapter: installation token (JWT app assertion), HMAC-verified webhooks, fetch model_card/policy/eval artifacts. → *backend E3.2, E3.3, E3.5*
- **INT-2** promptfoo/deepeval CI push (`POST /v1/ingest/eval`) reusing `parse_eval_run` exactly. → *backend E3.4*
- **INT-3** Per-source `try/except` isolation + `IngestionRun` idempotency + `/v1/tenant/{id}/integrations` health endpoint. → *backend E3.1, E2.4, E5.1*
- **INT-4** Manual Upload → Evidence Vault (minimal): drag-drop, type mapping, ingest-status polling, content-hash provenance. → *frontend F1–F3*

### Epic: ML-Assist (ML) — sourced from `ml-plan.md` (tickets A1–G2)
> ml-plan.md is the authoritative ML scope (21 tickets). Map: A1–A3 → ML-1 provider seam; B1–B3 → ML-1 index; C1–C3 → ML-1 suggestion; D1–D3 → ML-2 extraction; E1–E3 → ML-4 safety/audit log; F1–F3 → eval CI; G1–G2 → FE proposal surfaces. Drift (ML-3) ships as always-on core engine behavior, not an ML ticket (ml-plan §1).
- **ML-1** Evidence→control suggestion: local embedding (MiniLM) + pgvector/Chroma, curated control index from YAML catalogs, top-k + similarity + RAGAS faithfulness pre-check, human-confirm gate; per-control golden-set recall ≥0.90 CI gate. → *ml A1–A3, B1–B3, C1–C3, F1–F2*
- **ML-2** Structured field extraction (model cards / incidents): `instructor` + Pydantic, per-field confidence → `REVIEW` queue, human-confirm → immutable promote. → *ml D1–D3*
- **ML-3** Classical SPC drift alerts on `eval_run` time series (always-on, no flag — core engine, not ML). → *ml-plan §1 / ml-research §2c*
- **ML-4** `ACTREADY_PROVIDER` flag + `Provider` protocol (`NoneProvider`/`LocalProvider`/`OpenAIProvider`, default `none`) + append-only, sha256-hash-chained `ml_proposals` log with `parent_evidence_hash`. → *ml A1, E1–E3*

### Epic: Reporting (RPT)
- **RPT-1** Deterministic HTML→PDF via WeasyPrint (backend capability; UI button deferred to frontend H4). → *backend E4.1 (+ E4.2 diff), frontend H4*
- **RPT-2** Audit/Export View — Markdown + JSON generation/download + completeness bar. → *frontend G1–G2*
- **RPT-3** Signed, **revocable** read-only share link (JWT + `share_links` table, Flow C). → *backend E4.3, frontend H3*

### Epic: Frontend (FE)
- **FE-1** Readiness Scorecard / Overview (hero donut, framework cards, freshness strip, worst-first gaps, re-run). → *frontend C1–C4*
- **FE-2** Control Library View (framework tree, status filter, search, sortable rows). → *frontend D1–D3*
- **FE-3** Per-Control Detail Drawer (obligation mapping, remediation hint, freshness, linked evidence, `REVIEW-COUNSEL` badge). → *frontend E1–E3*
- **FE-4** Design system / PLG dev-tool tokens (light, dense, single blue accent, semantic status colors) — *frontend A4*

### Top-10 must-haves for v0.2 (strict priority order)
1. **FOUND-2** — RLS tenant isolation (security non-negotiable; backend E1.3).
2. **AUTH-1** — `get_principal` seam (everything hangs off it; backend E1.1).
3. **FOUND-3** — immutable, hash-chained evidence (auditor trust = the wedge; backend E2.1).
4. **INT-2** — promptfoo/deepeval CI push (reuses shipped parser; fastest path to a score; backend E3.4).
5. **FE-1** — Readiness Scorecard (the <1-hour aha moment; frontend C1–C4).
6. **FE-2** — Control Library (daily driver; shows derived-vs-asserted advantage; frontend D1–D3).
7. **INT-1** — GitHub App adapter (automatic, continuous evidence — the moat; backend E3.2/E3.3).
8. **RPT-2** — Audit/Export (Markdown + JSON) — the money artifact (frontend G1–G2).
9. **INT-3** — per-source error isolation (resilience; one bad token can't 422 the report; backend E3.1/E5.1).
10. **ML-1** — evidence→control suggestion behind flag (differentiation, zero liability when gated; ml A1–C3).

Items 1–9 are the hard floor for a shippable v0.2; **ML-1** is the highest-leverage "wow" that is safe because it is default-off and human-confirmed. Everything else (RPT-1 PDF capability, RPT-3 share link, FE-3 drawer, INT-4 vault, ML-2/3/4, FE-4 tokens) rounds out the milestone but may slip into a v0.2.x without breaking the theme.

**v0.2 ticket totals across plans:** Backend 22 (≈6 L / 11 M / 5 S) · Frontend 25+ (P0: 6 screens + foundation) · ML 21 (3 S / 15 M / 3 L). Combined, this is a coherent ~68-ticket release for a 4-person team across the 14-week M1–M4 sequence in §3.

---

### Cross-plan decisions already locked (carried from `research-deep-dive.md` §7, now resolved by the plans)
- **Evidence types:** keep the 4 engine types; `data_lineage`/`config_scan` deferred. *(backend §1 #1)*
- **Control catalog:** keep 39 (A.6 sub-split convention), delta documented. *(backend §1)*
- **Freshness:** `FRESH_DAYS=180` global; per-obligation event-driven (Art. 73) deferred to v0.3. *(backend §1 #4)*
- **Provider/Deployer role:** defer `role` param to v0.3; v0.2 scores the union. *(backend §1 #5)*
- **Omnibus:** versioned obligations file + per-report `catalog_version`; dates as data. *(backend E6.3)*
- **Wedge:** "evidence compiles itself from your pipelines" (reaffirmed vs all 12 competitors). *(backend §1 #8)*
- **PLG + paid trigger:** connected pipelines + audit-export. *(backend §1 #7, frontend §1 Q7)*
- **Deferred to v0.3+:** WorkOS/Clerk SSO, Stripe, Temporal, MLflow/HF/W&B + OpenLineage + PagerDuty, policy generator, risk-tier advisor, NL drafting, multi-workspace, auditor dashboards. *(backend §5; ml §1; frontend §1 P2)*
