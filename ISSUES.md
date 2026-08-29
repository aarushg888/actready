# ActReady v0.2 — Consolidated Issue Backlog

> Single source of truth for the v0.2 release. Derived from `docs/planning/*.md` (backend-plan, frontend-plan, ml-plan, product-plan) and `docs/*.md` research briefs.
> Authored by planning fan-out (2026-08-29). Status: **planning → ready for build**.

**Release theme:** *A startup can connect its ML pipeline and see a live, auditor-traceable readiness score in under one hour — no sales call, no questionnaire.*

**Timeline:** ~14 weeks, 4-person team (2 backend, 1 frontend, 1 ML/full-stack). Milestones M1–M4 below.
**Total tickets:** ~68 (Backend 22 · Frontend 25+ · ML 21).

---

## Milestones

| Milestone | Weeks | Ships | Exit criteria |
|---|---|---|---|
| **M1** Auth + DB + engine-multitenant | 1–4 | PyJWT `get_principal` seam, Postgres+SQLAlchemy2.0+Alembic, RLS isolation, tenant tables, engine behind service layer | Two tenants cannot read each other's data even if app code omits a filter |
| **M2** First 2 integrations + live scorecard | 4–9 | GitHub App adapter, promptfoo/deepeval CI push, immutable evidence store, per-source error isolation, Scorecard + Control Library + Detail Drawer | Connect a repo → scorecard with computed % + worst-first gaps in <5 min; broken token degrades one source, not the report |
| **M3** Report export + share link | 9–12 | WeasyPrint PDF (backend), versioned `report_snapshots`, signed revocable share link, Export view (Markdown+JSON) | Report reproduces byte-identically next week; external share link sees scorecard+evidence with no tenant creds |
| **M4** ML suggestion/extraction behind flag | 12–14 | Evidence→control suggestion (local embeddings), structured field extraction, all gated `ACTREADY_PROVIDER` default off | Golden-set recall ≥0.90/control before UI enabled; every proposal logged, human-confirm-gated |

---

## Epic: Foundations (FOUND)
- **FOUND-1** Postgres + SQLAlchemy 2.0 + Alembic baseline (`alembic upgrade head` on fresh PG). *→ backend E1.2*
- **FOUND-2** RLS tenant isolation: `app_owner`/`app_user` roles, `SET LOCAL app.tenant_id` GUC, `ENABLE`+`FORCE ROW LEVEL SECURITY`. *→ backend E1.3* — **[TOP-10 #1]**
- **FOUND-3** Immutable `evidence_artifacts` (DB trigger blocks UPDATE/DELETE) + sha256 content-hash + `/verify` recompute. *→ backend E2.1* — **[TOP-10 #3]**
- **FOUND-4** Versioned `report_snapshots` pinned to `catalog_version` + `manifest_hash` chaining (Omnibus dates as data). *→ backend E2.3, E6.3*

## Epic: Auth + Multi-tenant (AUTH)
- **AUTH-1** FastAPI + PyJWT `get_principal` dependency (sub/tenant_id/exp; no secrets in token). *→ backend E1.1* — **[TOP-10 #2]**
- **AUTH-2** Org/User/Membership schema + signup (`organizations` table; `viewer` role reserved for v0.4 auditor). *→ backend E1.4*
- **AUTH-3** Frontend auth + workspace shell (login/register, protected routes, sidebar, Zustand token store). *→ frontend A1–A4, B1–B3*

## Epic: Integrations (INT)
- **INT-1** GitHub App adapter: installation token (JWT), HMAC-verified webhooks, fetch model_card/policy/eval artifacts. *→ backend E3.2, E3.3, E3.5* — **[TOP-10 #7]**
- **INT-2** promptfoo/deepeval CI push (`POST /v1/ingest/eval`) reusing `parse_eval_run` exactly. *→ backend E3.4* — **[TOP-10 #4]**
- **INT-3** Per-source `try/except` isolation + `IngestionRun` idempotency + `/v1/tenant/{id}/integrations` health. *→ backend E3.1, E2.4, E5.1* — **[TOP-10 #9]**
- **INT-4** Manual Upload → Evidence Vault (drag-drop, type mapping, ingest-status polling, content-hash provenance). *→ frontend F1–F3*

## Epic: ML-Assist (ML) — authoritative scope in `ml-plan.md` (21 tickets A1–G2)
- **ML-1** Evidence→control suggestion: local embedding (MiniLM) + pgvector/Chroma, curated control index, top-k + similarity + RAGAS faithfulness pre-check, human-confirm gate; per-control golden-set recall ≥0.90 CI gate. *→ ml A1–A3, B1–B3, C1–C3, F1–F2* — **[TOP-10 #10]**
- **ML-2** Structured field extraction (model cards / incidents): `instructor` + Pydantic, per-field confidence → `REVIEW` queue, human-confirm → immutable promote. *→ ml D1–D3*
- **ML-3** Classical SPC drift alerts on `eval_run` time series (always-on, no flag — core engine, not ML). *→ ml-plan §1*
- **ML-4** `ACTREADY_PROVIDER` flag + `Provider` protocol (None/Local/OpenAI, default `none`) + append-only sha256-hash-chained `ml_proposals` log with `parent_evidence_hash`. *→ ml A1, E1–E3*

## Epic: Reporting (RPT)
- **RPT-1** Deterministic HTML→PDF via WeasyPrint (**backend capability**; UI button deferred to frontend H4). *→ backend E4.1, frontend H4*
- **RPT-2** Audit/Export View — Markdown + JSON generation/download + completeness bar. *→ frontend G1–G2* — **[TOP-10 #8]**
- **RPT-3** Signed, **revocable** read-only share link (JWT + `share_links` table). *→ backend E4.3, frontend H3*

## Epic: Frontend (FE)
- **FE-1** Readiness Scorecard / Overview (hero donut, framework cards, freshness strip, worst-first gaps, re-run). *→ frontend C1–C4* — **[TOP-10 #5]**
- **FE-2** Control Library View (framework tree, status filter, search, sortable rows). *→ frontend D1–D3* — **[TOP-10 #6]**
- **FE-3** Per-Control Detail Drawer (obligation mapping, remediation hint, freshness, linked evidence, `REVIEW-COUNSEL` badge). *→ frontend E1–E3*
- **FE-4** Design system / PLG dev-tool tokens (light, dense, single blue accent, semantic status colors). *→ frontend A4*

---

## Top-10 must-haves for v0.2 (strict priority)
1. **FOUND-2** RLS tenant isolation (security non-negotiable)
2. **AUTH-1** `get_principal` seam (everything hangs off it)
3. **FOUND-3** immutable, hash-chained evidence (auditor trust = the wedge)
4. **INT-2** promptfoo/deepeval CI push (reuses shipped parser; fastest path to a score)
5. **FE-1** Readiness Scorecard (the <1-hour aha moment)
6. **FE-2** Control Library (shows derived-vs-asserted advantage)
7. **INT-1** GitHub App adapter (continuous evidence = the moat)
8. **RPT-2** Audit/Export (Markdown + JSON) — the money artifact
9. **INT-3** per-source error isolation (one bad token can't 422 the report)
10. **ML-1** evidence→control suggestion behind flag (safe differentiation)

Items 1–9 are the hard floor; **ML-1** is the highest-leverage "wow" that is safe because default-off + human-confirmed.

---

## Explicitly deferred (NOT v0.2)
Enterprise SSO (WorkOS/Clerk) · Stripe billing · Temporal · Runtime/production monitoring (Fiddler/Arthur lane) · Policy/Playbook generator · ML risk-tier advisor · NL remediation drafting · MLflow/HF/W&B + OpenLineage + PagerDuty connectors · multi-workspace · auditor dashboards. Each has an entry trigger documented in `backend-plan.md §5` / `ml-plan.md §1` / `frontend-research.md §1`.

## Metrics & kill criteria
- Activation: median time-to-first-score < 60 min (best-case <5 min)
- Retention: ≥30% weekly re-assessment rate by week 8
- Evidence-source connected: median ≥2 per active tenant
- ML acceptance: ≥0.70 where enabled; override >15% on any control for 2 weeks → rollback
- **Kill:** <3 paid pilots in 90 days → pause paid motion, return to free-tier loop
