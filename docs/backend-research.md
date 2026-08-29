# ActReady — Backend / Platform Research Brief

**Status:** Research only (no code). **Scope:** v0.2+ platform design.
**Author:** Backend/platform research agent. **Date:** 2026-08-29.
**Grounding:** v0.1 repo at `/api` — FastAPI `POST /assess` (multipart files[]), deterministic
`app.ingest` → `app.mapper` → `app.report`, pydantic models in `app/models.py`, versioned YAML
catalogs in `data/` (39 ISO 42001 controls, 21 EU AI Act obligations). All citations are real
doc URLs; items I reason about but cannot confirm from a primary source are marked **UNVERIFIED**.

---

## 1. Architecture for Multi-Tenant SaaS

v0.1 is single-tenant by construction: one process, one in-memory `collect_evidence` call, no
persistence. Moving to multi-tenant SaaS means introducing (a) identity, (b) a tenant-scoped
datastore, (c) an org/team model, (d) billing, and (e) durable background work for continuous
ingestion. The deterministic engine does not change — it becomes a pure function called by a
tenant-aware service layer.

### 1.1 Auth: JWT vs Clerk/WorkOS
For PLG (product-led growth) with team invites and, eventually, enterprise SSO, a managed
auth provider is the right v0.2 bet. Two credible options:

- **Clerk** — best-in-class React/TS embedded UI, org/team primitives (B2B SaaS plan),
  passwordless + social + MFA out of the box. Pricing scales with MAU; SSO is a per-org add-on
  (~$50/org/mo). Good if the app frontend is React-first and you want zero auth UI work.
  Ref: https://clerk.com
- **WorkOS** — built for B2B/enterprise from day one: SAML/OIDC SSO, SCIM directory sync,
  audit logs, fine-grained authz. AuthKit covers full auth (1M users free); SSO is
  ~$125/connection/mo. Better fit if enterprise SSO + SCIM is the actual sales blocker.
  Ref: https://workos.com/compare/clerk

**Recommendation:** Start with **FastAPI + PyJWT** (or `python-jose`) for v0.2 to keep the MVP
dependency-light and fully in-repo, with the auth layer behind a thin `get_principal`
dependency so you can swap to Clerk/WorkOS (or a B2B auth SDK) later without touching the engine.
Adopt **WorkOS AuthKit** when the first enterprise SSO deal appears. Either way, the JWT should
carry `sub` (user), `tenant_id` (org), and `exp`; never put org secrets in the token. FastAPI
auth docs: https://fastapi.tiangolo.com/tutorial/security/

### 1.2 Tenant isolation: row-level security in Postgres
The cleanest, defense-in-depth isolation is **PostgreSQL Row-Level Security (RLS)** on a
single shared schema, rather than schema-per-tenant (migration/connection sprawl) or
app-only `WHERE tenant_id =` filtering (fragile). Pattern (verified in the
`fastapi-rls-multi-tenant` reference design):

1. Two DB roles: `app_owner` (DDL via Alembic) and `app_user` (runtime DML, subject to RLS,
   **never** superuser).
2. On every request, a FastAPI dependency runs `SET LOCAL app.tenant_id = :tenant` inside the
   transaction (transaction-local GUCs auto-reset on commit — no stale context leaks across
   pooled connections).
3. Each tenant-scoped table gets `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
   (covers even the table owner) with a `USING (tenant_id = current_setting('app.tenant_id'))`
   policy.

This guarantees isolation even if application code forgets a filter. Ref (pattern):
https://github.com/rabinhansda24/fastapi-rls-multi-tenant

**ORM choice:** SQLAlchemy 2.0 + Alembic is the safest, best-documented pairing for RLS +
migrations. SQLModel is attractive (FastAPI-flavored, used by the reference RLS example) but
is thinner on advanced Postgres features; pick **SQLAlchemy 2.0 + Alembic** for v0.2 and keep
the pydantic models as the API contract. **UNVERIFIED:** exact Alembic+RLS migration ordering
(e.g., whether RLS policies are best applied in a post-deploy hook vs. inline DDL) needs a spike.

### 1.3 Org / team model
Minimal first model: `tenants` (org), `users`, `memberships` (user↔tenant, role:
owner/admin/member/viewer), `invites`. The auditor "read-only" role (in the v0.4 roadmap) maps
to a `viewer` who can fetch reports/snapshots but not mutate evidence. **UNVERIFIED:** whether
to support multiple workspaces *per* tenant (the roadmap says "multi-workspace API") — defer;
start with one workspace per tenant.

### 1.4 Billing: Stripe
Use **Stripe Billing** with Checkout Sessions (`mode: 'subscription'`) for the happy path and
the **Customer Portal** for self-serve upgrade/downgrade/cancel — you avoid building a billing
UI. Webhooks (`customer.subscription.*`, `invoice.payment_failed`) are the source of truth for
access state; verify with `stripe.webhooks.constructEvent(body, sig, WEBHOOK_SECRET)` and store
processed `event.id`s idempotently. Subscriptions drive a `plan` field on the tenant that gates
feature access (e.g., number of connected integrations, report history depth).
Refs: https://docs.stripe.com/billing/subscriptions/build-subscriptions ,
https://docs.stripe.com/webhooks

### 1.5 Background jobs & durable ingestion
Continuous ingestion (Section 2) needs a job queue. Three realistic options:

- **ARQ** — asyncio-native, Redis-backed, tiny, `enqueue_job`/`Retry`/cron built in; fits
  FastAPI's event loop cleanly. Caveat: **the project is in maintenance-only mode**
  (python-arq/arq#510). Fine for v0.2 but not a long-term bet. Ref: https://arq-docs.helpmanual.io/
- **Celery** — battle-tested, large ecosystem, but heavier (broker + workers) and less
  asyncio-friendly.
- **Temporal** — durable, replayable workflows; ideal if ingestion becomes long-running and
  must survive crashes mid-pipeline without duplicate side effects. Higher ops cost (or
  Temporal Cloud). Ref: https://temporal.io

**Recommendation:** use **ARQ for v0.2** to ship fast, structure ingestion behind a stable
`IngestionJob` interface, and keep **Temporal** as the documented upgrade path for durable,
multi-step ingestion.

---

## 2. Integration Architecture (continuous evidence, not just upload)

The core design principle: every integration is an **adapter** that calls a source API (push
webhook or polling), normalizes output into the existing `Evidence` shape (`app/ingest.py`),
and enqueues it as an ingestion job. One adapter failing must not affect others (see Section 5).

| Source | Auth model | Push vs poll | Rate limits | Evidence → controls (examples) |
|---|---|---|---|---|
| **GitHub App** | Installation access token (JWT-signed app assertion → `POST /app/installations/{id}/access_tokens`); webhooks HMAC-SHA256 via `X-Hub-Signature-256` | **Both**: webhooks for PR/run events, poll for artifact fetch | 5,000 req/hr/user; GitHub App installation tokens scale with repos+users; 15,000/hr on GHEC | CI artifacts (eval JSON) → eval controls; repo policy/README → `policy`; PR approvals → governance evidence |
| **MLflow / Hugging Face / W&B** | MLflow: HTTP Basic or Bearer token (no auth by default — must front with proxy/auth) | Poll (REST) | MLflow: none enforced (self-hosted); HF/W&B: per-plan API limits | Model registry metadata, run metrics, training params → `model_card` / data-governance controls |
| **promptfoo / deepeval (CI)** | Pull artifact from GitHub Actions / CI storage, or push export to ingest endpoint | Push (CI uploads JSON) or poll job artifacts | inherits CI limits | Eval runs → `eval_run` (already parsed by `app/ingest.parse_eval_run`) |
| **incident.io / PagerDuty** | OAuth2 (incident.io) or API key/REST token (PagerDuty) | **Push** webhooks | PagerDuty: 1,800/20s per key; incident.io: generous, per-plan | Incident post-mortems → `incident_log` (matches `parse_incidents` schema) |
| **OpenLineage** | HTTP transport, optional auth on collector | **Push** (lineage events) | n/a (self-deployed collector) | Dataset/job lineage → data-governance (Art. 10) + model provenance evidence |

**GitHub Apps — concrete:** a GitHub App is the correct auth primitive (not PAT/OAuth app):
the app is identified by an `APP_ID` + `PRIVATE_KEY`, mints short-lived installation tokens,
and subscribes to `workflow_run`/`pull_request` events. Webhook delivery must be verified with
HMAC-SHA256 against the app webhook secret before trust. Refs:
https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation ,
https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries ,
https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api

**MLflow REST API:** `POST /api/2.0/mlflow/runs/search` and `GET /experiments/search` return
runs/metrics; pagination via `page_token`. Auth is Basic or Bearer; self-hosted servers ship
with **no auth**, so a production ActReady connector should only talk to an auth-fronted
tracking server. Ref: https://mlflow.org/docs/latest/api_reference/rest-api.html

**OpenLineage:** open JSON schema (`RunEvent`/`DatasetEvent`/`JobEvent`) over an HTTP API;
ActReady would run as a **consumer** of a self-hosted collector (e.g., Marquez) and map
`inputs`/`outputs` datasets + job metadata to data-governance controls. Ref:
https://openlineage.io/ , https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md

**UNVERIFIED:** the precise control→source mapping table above is a first-pass heuristic; it
should be encoded as data (a `source_to_evidence_type` + `evidence_type_to_controls` config) and
reviewed against the catalogs, not hardcoded.

---

## 3. Storage & Evidence Model

The v0.1 `Evidence` pydantic model (`type`, `content`, `collected_at`, `source_name`) is the
right unit but needs persistence, versioning, immutability, and tamper-evidence.

### 3.1 Tables (Postgres, RLS-scoped on `tenant_id`)
- `tenants`, `users`, `memberships`, `invites` (Section 1).
- `evidence_artifacts` — one row per ingested artifact: `id`, `tenant_id`, `evidence_type`
  (model_card|eval_run|incident_log|policy), `source` (e.g. `github:org/repo`),
  `raw_payload` (JSONB), `content_hash` (sha256 of canonicalized payload), `collected_at`,
  `ingested_at`, `integration_run_id` (FK), `immutable=true`.
- `control_mappings` — `evidence_id`, `control_id`, `obligation_id`, `status`
  (satisfied|partial|missing), `score`, `mapped_at`. Recomputed by the engine, not edited by hand.
- `ingestion_runs` — `id`, `tenant_id`, `source`, `status` (success|partial|failed),
  `started_at`, `finished_at`, `error` (truncated), `items_ingested`.
- `reports` / `report_snapshots` — versioned, point-in-time `GapReport` output (Section 4).

### 3.2 Immutability & tamper-evidence (auditor-friendly)
- **Append-only artifacts.** Once written, `evidence_artifacts` rows are never `UPDATE`/`DELETE`
  (enforce with a DB trigger, mirroring the `case_events` RLS reference pattern). A new version
  is a *new row* with a new `content_hash`; the old row stays.
- **Content hashing.** Store `sha256(canonical_json(raw_payload))`. Expose a `/verify` endpoint
  that recomputes and compares, so an auditor can prove evidence was not altered since ingest.
  Add a top-level `manifest_hash` per `report_snapshot` chaining artifact hashes.
- **Freshness.** Keep `collected_at` (when the source event happened) separate from
  `ingested_at` (when ActReady saw it). Scoring already uses a 180-day window; persist the
  computed `evidence_age_days` so reports are reproducible.

### 3.3 Versioning
Catalogs (`data/*.yaml`) are already versioned (`version:` + `updated:`). Pin each
`report_snapshot` to the catalog `version` used, so a control-definition change doesn't silently
rewrite history. **UNVERIFIED:** whether to store full catalog snapshots per report or just a
version pointer — pointer + changelog is sufficient for v0.2.

---

## 4. Reporting / Export

Auditors want stable, diffable, shareable artifacts. Three layers:

1. **Deterministic render.** Reuse `app/report.render_markdown` but produce a canonical HTML
   first (Jinja2 template over the `GapReport` model). From HTML, generate **PDF via
   WeasyPrint** (`HTML(string=html).write_pdf()`) — open-source, local, supports CSS paged
   media, no external service. (WeasyPrint requires Python 3.10+, system libs Pango/HarfBuzz.)
   Alternative: `reportlab` for programmatic PDF if layout control matters more than HTML reuse.
   Refs: https://weasyprint.org/ , https://www.nutrient.io/blog/how-to-generate-pdf-reports-from-html-in-python/
2. **Versioned snapshots.** Each `POST /assess`-equivalent (or scheduled re-run) writes a
   `report_snapshot` with its own `manifest_hash` and catalog version. This yields
   **diffable reports over time** (a roadmap item) — store two snapshots, compute the delta on
   controls whose status changed.
3. **Audit room share link.** A `reports/{snapshot_id}/share` endpoint issues a time-limited,
   signed token (e.g., FastAPI `encode_jwt` with short `exp`) granting read-only access to one
   snapshot — the v0.4 "auditor read-only views" without giving away the tenant.
   **UNVERIFIED:** retention policy for shared links (recommend 30-day expiry, revocable).

---

## 5. Observability & Reliability (the resilience bug class)

**The known failure mode:** v0.1's `assess` runs `collect_evidence` inline; a malformed file
raises `IngestError` and the whole request 422s. At multi-tenant scale with live integrations,
a single flaky source (expired token, rate-limit 403, schema drift) must **never** crash the
assessment or block other sources. This is the Places-style "one bad input kills the page" bug.

### 5.1 Error-isolation pattern
Wrap each adapter's `fetch → normalize → store` in its own `try/except`; on failure, record an
`ingestion_runs` row with `status='failed'` + truncated `error`, and **continue**. The
aggregate report is computed from *available* evidence, and each control's coverage notes which
sources contributed and which failed.

```
for source in enabled_sources(tenant):
    try:
        run_ingestion(source)            # isolated
    except AdapterError as e:
        log.warning(...); record_run(status="failed", error=str(e)[:500])
        # do NOT re-raise
report = build_report(tenant, only_successful_runs=True)
report.coverage = {src: run.status for src, run in runs}
```

### 5.2 Status dashboard
Surface per-source health in the UI and `/v1/tenant/{id}/integrations`:
`connected | degraded (N failures) | disconnected`. Emit metrics (ingestion latency, failure
count, evidence age) to your observability stack (e.g., OpenTelemetry → whatever the team uses).
**UNVERIFIED:** specific SLO targets (recommend: ≥99% per-source job success, alert on 3
consecutive failures).

### 5.3 Determinism preserved
The engine stays pure and deterministic (same inputs → same `GapReport`). Non-determinism lives
only in *fetching* inputs, which are snapshotted as immutable artifacts — so a report is always
reproducible from stored evidence regardless of source availability at render time.

---

## 6. Open Questions (for planning)

1. **Workspace granularity:** one workspace per tenant (v0.2) vs. many workspaces per tenant
   (roadmap "multi-workspace API")? Affects every schema decision.
2. **Auth build vs. buy:** FastAPI+JWT in-house now, or adopt WorkOS/Clerk at v0.2? Depends on
   whether enterprise SSO is a near-term sales requirement.
3. **RLS vs. schema-per-tenant:** RLS chosen here, but is the ops team comfortable managing
   transaction-local GUCs in the connection pool (SQLAlchemy `pool_pre_ping` + `SET LOCAL`
   hooks)?
4. **Job queue longevity:** ARQ (maintenance-only) acceptable for v0.2, or go straight to
   Temporal/Celery to avoid a later migration?
5. **Evidence retention & deletion:** immutable artifacts complicate GDPR "right to erasure" —
   do we need crypto-shredding or tenant-level purge, and how does that interact with audit
   immutability expectations?
6. **Control→source mapping ownership:** who maintains the `source_to_controls` config, and how
   often does it change vs. the catalogs?
7. **Report reproducibility window:** how many historical `report_snapshots` per tenant must we
   keep (storage cost vs. audit-need)? Recommend ≥24 months given EU AI Act 10-year documentation
   expectation — **UNVERIFIED** whether we store full snapshots or deltas.
8. **Webhook ingestion at scale:** do we need a dedupe/ordering layer (e.g., idempotency keys on
   `ingestion_runs`) for at-least-once webhook delivery from incident.io/PagerDuty?

---

## BACKEND MVP SCOPE — v0.2 recommendation

Build the smallest thing that turns ActReady from a CLI into a tenant-aware service with live
evidence, in this order:

1. **Auth + DB foundation.** FastAPI + PyJWT `get_principal`, Postgres + SQLAlchemy 2.0/Alembic,
   RLS tenant isolation, `tenants/users/memberships` tables. Engine called behind a
   tenant-scoped service. *(No external auth vendor yet — keep the seam.)*
2. **Evidence persistence.** `evidence_artifacts` (immutable, sha256), `control_mappings`,
   `ingestion_runs`; keep `app/ingest` parsers as the normalization layer.
3. **Two integrations first** (highest signal, lowest auth friction):
   - **GitHub App** (push webhooks + poll for eval artifacts) — covers eval + policy evidence.
   - **promptfoo/deepeval via CI push** (upload eval JSON to an ingest endpoint) — reuses the
     existing parser exactly.
   Each behind the isolated adapter pattern from Section 5.
4. **Report export.** Deterministic HTML→PDF (WeasyPrint) + versioned `report_snapshots` +
   signed read-only share link.
5. **Reliability baseline.** Per-source `try/except` isolation, `ingestion_runs` status, and a
   minimal integrations health endpoint.

**Explicitly deferred to v0.3+:** WorkOS/Clerk swap, Stripe billing, MLflow/HF/W&B + OpenLineage
connectors, incident.io/PagerDuty webhooks, multi-workspace, auditor dashboards. This MVP makes
the product multi-tenant and continuously-fed while keeping the deterministic, auditor-trustworthy
core intact.
