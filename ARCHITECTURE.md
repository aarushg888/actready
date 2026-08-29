# ActReady — Architecture Sketch (v0.1 → v0.2)

> Target-state architecture for the v0.2 multi-tenant SaaS, derived from `docs/planning/*.md`. The v0.1 engine is the deterministic system of record and is NOT replaced — it gains a tenant-scoped service layer and opt-in ML assistance.

## v0.1 (today, single-tenant CLI/API)
```
evidence files (model_card.yaml, promptfoo/deepeval .json, incidents.csv)
        │  ingest.collect_evidence (typed parsers: IngestError on bad field)
        ▼
mapper.map_evidence(evidence, controls, today)
        │  deterministic: satisfied / partial (stale >180d) / missing
        ▼
GapReport (summary.readiness_score, items[].status, remediation_hint)
        │  report.render_markdown
        ▼
FastAPI POST /assess  (multipart files[])  +  GET /healthz
```
Deterministic, no DB, no auth, no ML in the scoring path. `ACTREADY_PROVIDER` env already exists (default `none`) for optional NL explanations.

## v0.2 (target)
```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (Vite + React + TS + Tailwind + shadcn/ui)                 │
│  Scorecard · Control Library · Detail Drawer · Evidence Vault · Export│
│  Auth shell (Zustand token) · TanStack Query · openapi-typescript      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS (JWT Bearer)
┌───────────────────────────▼─────────────────────────────────────────┐
│  FastAPI app (app.main)                                              │
│  get_principal (PyJWT) ──> tenant_id ──> SET LOCAL app.tenant_id     │
│   POST /auth/*   GET /api/readiness   GET /api/controls[/:id]        │
│   POST /api/evidence   POST /v1/ingest/eval   GET /api/report        │
│   GET /v1/tenant/{id}/integrations (health)                         │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────────────┐
        ▼                   ▼                           ▼
┌──────────────┐   ┌────────────────────┐   ┌──────────────────────┐
│ Assessment   │   │ Integration adapters│   │ ML-Assist (flagged)   │
│ Service       │   │ EvidenceSource Proto│   │ ACTREADY_PROVIDER     │
│ (tenant scope)│   │  GitHub App adapter │   │  NoneProvider (default)│
│  loads arts → │   │  promptfoo/CI push │   │  LocalProvider (MiniLM)│
│  map_evidence │   │  (per-source try/  │   │  OpenAIProvider        │
│  (PURE, kept) │   │   except isolation)│   │  suggestion/extraction │
└──────┬───────┘   └─────────┬──────────┘   └───────────┬──────────┘
       │                     │                          │ proposals
       │                     │ evidence_artifacts       │ (human-confirm)
       ▼                     ▼                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  Postgres (RLS-enabled)                                             │
│   organizations · users · memberships · integration_connections      │
│   evidence_artifacts (IMMUTABLE, sha256, manifest_hash)             │
│   control_mappings · ingestion_runs · report_snapshots              │
│   share_links · ml_proposals (append-only, hash-chained)           │
│   RLS: FORCE ROW LEVEL SECURITY on tenant-scoped tables             │
└──────────────────────────────────────────────────────────────────┘
        │                                              │
        ▼                                              ▼
 WeasyPrint (deterministic HTML→PDF)          ARQ job queue (ingestion)
 report_snapshots (catalog_version-pinned)     signed revocable share link (JWT)
```

## Key invariants (from the plans)
1. **Deterministic engine is system of record.** `map_evidence` stays pure; ML only *proposes* control mappings, never decides. Every proposal is logged (model/version/prompt/raw I/O) and requires human confirmation to promote.
2. **Evidence is immutable + tamper-evident.** `evidence_artifacts` rejects UPDATE/DELETE (DB trigger); content sha256 + `manifest_hash` chaining. This is the audit wedge vs incumbents that *assert* control status.
3. **One flaky source never 422s the report.** `EvidenceSource` implementations wrapped in `try/except`; failures recorded in `ingestion_runs` and surfaced via the health endpoint, not raised.
4. **Tenant isolation by RLS, not app filters alone.** Transaction-local `app.tenant_id` GUC + `FORCE ROW LEVEL SECURITY` — defense-in-depth even if a query forgets the WHERE clause.
5. **Law dates as data.** `catalog_version` pins the obligation set per report; Digital Omnibus (Reg 2026/1744) deferral (high-risk → 2 Dec 2027) is a catalog row, not a code change.
6. **ML runs without API keys by default.** Local open-weight embeddings (all-MiniLM-L6-v2 / bge-small-en-v1.5) + pgvector/Chroma; `LocalProvider` is the zero-config default.

## Data model (skeletons — see `backend-plan.md §2` for full)
- `Organization(id, name, created_at)`
- `User(id, email, hashed_pw)`
- `Membership(user_id, org_id, role)`  (`viewer` reserved v0.4)
- `IntegrationConnection(id, org_id, type, creds_encrypted, last_sync, status)`
- `EvidenceArtifact(id, org_id, type, sha256, manifest_hash, collected_at, ingested_at, source_run_id)` — immutable
- `ControlMapping(artifact_id, control_id, obligation_id, status, suggested_by_ml, confirmed)`
- `IngestionRun(id, org_id, source, status, error, started_at, finished_at)`
- `ReportSnapshot(id, org_id, catalog_version, manifest_hash, rendered_at)`
- `ShareLink(token, org_id, expires_at, revoked)`

## Integration adapter contract (`backend-plan.md §3`)
```python
from typing import Protocol
class EvidenceSource(Protocol):
    def fetch(self) -> list[RawEvidence]: ...   # raises only into the isolation wrapper
# isolation wrapper: try: fetch() except Exception as e: record(IngestionRun.error=e); continue
```
v0.2 ships: **GitHub App** (installation JWT + HMAC webhooks) and **promptfoo/deepeval CI push** (`POST /v1/ingest/eval`, reuses existing parser). MLflow/HF/W&B deferred.

## API contract the frontend assumes (`frontend-plan.md §3`)
`POST /auth/login|register` · `GET /api/readiness` · `GET /api/controls` · `GET /api/controls/:id` · `POST /api/evidence` · `GET /api/report[?format=pdf]`. Shapes derived from `GapReport`/`GapItem` (`readiness_score`, `status` ∈ {satisfied,partial,missing}, `remediation_hint`, `evidence_age_days`).

## Scope split (ratified)
- Backend PDF generation (`GET /api/report?format=pdf`) ships in v0.2.
- Frontend PDF *button* deferred to P1/v0.3 (H4). Markdown + JSON export ships P0.
