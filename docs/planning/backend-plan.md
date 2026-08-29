# ActReady Backend v0.2 — Scope & Plan

**Author:** Backend planning agent · **Date:** 2026-08-29 · **Status:** Decision-locked for v0.2
**Resolves:** `backend-research.md` (§6 open questions, BACKEND MVP SCOPE), `research-deep-dive.md` (§ SCOPE QUESTIONS 1–10), aligned to `frontend-research.md` (§5–6) and `ml-research.md` (deterministic engine is system of record).

The deterministic engine (`app/mapper.map_evidence`) does **not** change in v0.2. It becomes a pure function called by a tenant-aware service layer. Every decision below protects that invariant.

---

## 1. v0.2 Backend Scope — Decisions

| # | Item | Decision | Rationale |
|---|------|----------|-----------|
| 1 | Auth (PyJWT `get_principal` seam) | **ACCEPT** | Build in-house FastAPI + PyJWT behind a thin `get_principal` dependency. No Clerk/WorkOS for v0.2 (frontend §5 Q1, backend §6 Q2). Token carries `sub`, `tenant_id`, `exp`; never org secrets. Swap to WorkOS when the first enterprise SSO deal appears. |
| 2 | Postgres + SQLAlchemy 2.0 + Alembic | **ACCEPT** | Over SQLModel (backend §1.2) — best-documented RLS + migration pairing. Pydantic models stay the API contract. |
| 3 | RLS tenant isolation | **ACCEPT** | Row-Level Security on a shared schema, `ENABLE`+`FORCE RLS`, policy `USING (tenant_id = current_setting('app.tenant_id'))`. Transaction-local GUC via `SET LOCAL` (auto-resets on commit — no stale-context leak on pooled connections). Two roles: `app_owner` (Alembic DDL) and `app_user` (runtime DML, never superuser). |
| 4 | ARQ job queue | **ACCEPT** | asyncio-native, Redis-backed, fits FastAPI event loop. Wrapped behind a stable `IngestionJob` interface; **Temporal** is the documented upgrade path (backend §1.5). |
| 5 | Two integrations | **ACCEPT — GitHub App + promptfoo/deepeval-from-CI** (justified §3) | Highest signal, lowest auth friction, reuses existing parser. MLflow/HF/W&B poll deferred (no auth by default = security risk, lower immediate yield). |
| 6 | WeasyPrint report export | **ACCEPT** | Deterministic HTML (Jinja2 over `GapReport`) → PDF via `HTML(string=html).write_pdf()`. Local, open-source, no external service. |
| 7 | Signed share link | **ACCEPT** | Time-limited, scoped, **revocable** JWT (`exp` + `jti` tracked in a `share_links` table). Read-only access to one snapshot — the v0.4 auditor view without exposing the tenant. |

**Deep-dive scope questions resolved:** (1) keep the 4 evidence types — `data_lineage`/`config_scan` deferred; (3) keep 39-control catalog, document delta as A.6 sub-split convention; (4) keep `FRESH_DAYS=180` globally, per-obligation event-driven freshness (Art. 73) deferred to v0.3; (5) defer Provider/Deployer role scoping to v0.3 — v0.2 scores the union; (6) versioned obligations file + per-report `catalog_version` pointer, Omnibus dates as data; (7) PLG confirmed, paid trigger = connected pipelines + audit-export; (8) wedge = **"evidence compiles itself from your pipelines"**; (9) PDF/JSON/Markdown from v0.2, readiness-over-time from snapshots; (10) trust via sha256 + manifest_hash + `/verify` + signed links in v0.2.

---

## 2. Data Model — SQLAlchemy 2.0 Skeletons

All tenant-scoped tables carry `org_id` (= the RLS `tenant_id` key) and an `RLS` mixin. RLS is applied in a post-deploy Alembic hook (backend §1.2 UNVERIFIED spike resolved: **inline DDL in migration is fragile; apply RLS policies in a dedicated `enable_rls` migration that runs after all tables exist**).

```python
from __future__ import annotations
import datetime as dt
import uuid
from sqlalchemy import String, Text, Boolean, DateTime, Date, ForeignKey, LargeBinary, JSON, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase): pass

class Organization(Base):
    """Tenant. `id` is the RLS tenant key; `plan` gates feature access (Stripe later)."""
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(32), default="free")  # free|team|scale
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="org")

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

class Membership(Base):
    """user <-> org with role. `viewer` = auditor read-only (v0.4)."""
    __tablename__ = "memberships"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="member")  # owner|admin|member|viewer
    org: Mapped["Organization"] = relationship(back_populates="memberships")
    __table_args__ = (UniqueConstraint("org_id", "user_id"),)

class IntegrationConnection(Base):
    """Per-org connector config. `creds_encrypted` is envelope-encrypted (KMS/Fernet)."""
    __tablename__ = "integration_connections"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # github_app|promptfoo_ci
    creds_encrypted: Mapped[bytes] = mapped_column(LargeBinary)  # never plaintext
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # repo list, webhook id, etc.
    status: Mapped[str] = mapped_column(String(16), default="connected")  # connected|degraded|disconnected
    last_sync: Mapped[dt.datetime | None] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    __table_args__ = (UniqueConstraint("org_id", "type"),)

class EvidenceArtifact(Base):
    """Immutable, tamper-evident. Never UPDATE/DELETE (DB trigger enforces). New version = new row."""
    __tablename__ = "evidence_artifacts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(32))  # model_card|eval_run|incident_log|policy
    source: Mapped[str] = mapped_column(String(255))  # e.g. github:org/repo
    raw_payload: Mapped[dict] = mapped_column(JSON)  # canonicalized
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # sha256(canonical_json)
    manifest_hash: Mapped[str | None] = mapped_column(String(64))  # per-report chain (set on snapshot)
    collected_at: Mapped[dt.date] = mapped_column(Date)  # when the source event happened
    ingested_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    mappings: Mapped[list["ControlMapping"]] = relationship(back_populates="artifact")

class ControlMapping(Base):
    """Recomputed by the engine, never hand-edited."""
    __tablename__ = "control_mappings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_artifacts.id"), index=True)
    control_id: Mapped[str] = mapped_column(String(64), index=True)
    obligation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))  # satisfied|partial|missing
    score: Mapped[float | None] = mapped_column()
    catalog_version: Mapped[str] = mapped_column(String(32))
    mapped_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    artifact: Mapped["EvidenceArtifact"] = relationship(back_populates="mappings")

class IngestionRun(Base):
    """Per-source job record; powers health dashboard + idempotency."""
    __tablename__ = "ingestion_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    source: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)  # at-least-once dedupe
    status: Mapped[str] = mapped_column(String(16))  # success|partial|failed
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(String(500))  # truncated
    items_ingested: Mapped[int] = mapped_column(default=0)

class ReportSnapshot(Base):
    """Versioned, point-in-time GapReport. Diffable over time."""
    __tablename__ = "report_snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    catalog_version: Mapped[str] = mapped_column(String(32))
    manifest_hash: Mapped[str] = mapped_column(String(64))  # chains artifact content_hashes
    report_json: Mapped[dict] = mapped_column(JSON)  # full GapReport (cheap; audit needs it)
    framework_scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    generated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

class ShareLink(Base):
    """Revocable, time-limited read-only access to one snapshot."""
    __tablename__ = "share_links"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_snapshots.id"), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True)  # JWT id
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
```

**GDPR / right-to-erasure (backend §6 Q5):** artifacts are immutable *within* a tenant, but erasure is satisfied by **tenant-level purge** (`DELETE ... WHERE org_id =` outside RLS, or crypto-shredding the org key). Full per-artifact crypto-shredding deferred post-GA; document the path now.

---

## 3. Integration Adapter Interface

`EvidenceSource` is a Protocol. Each adapter normalizes a source into the existing `Evidence` shape (`app/ingest.py`) and enqueues an ingestion job. **Error isolation (backend §5):** each adapter's `fetch → normalize → store` runs in its own `try/except`; failure writes an `ingestion_runs` row (`status='failed'`, truncated `error`) and **continues** — one bad source never blocks the assessment.

```python
class RawEvidence(BaseModel):
    evidence_type: str            # one of the 4 engine types
    content: dict[str, object]
    collected_at: dt.date
    source_name: str

class EvidenceSource(Protocol):
    name: str
    def fetch(self, conn: IntegrationConnection) -> list[RawEvidence]: ...

class GitHubSource:
    """GitHub App: installation token (JWT app assertion) + HMAC-verified webhooks.
    Polls repos for model_card.yaml, policy docs, and CI eval artifacts."""
    name = "github_app"
    def fetch(self, conn) -> list[RawEvidence]:
        token = mint_installation_token(conn)            # short-lived
        artifacts = []
        for repo in conn.config["repos"]:
            card = get_file(repo, "model_card.yaml", token)   # -> model_card
            policy = get_file(repo, "docs/ai-policy.md", token)  # -> policy
            eval_json = get_latest_workflow_artifact(repo, token)  # -> eval_run
            artifacts += [normalize(c) for c in (card, policy, eval_json) if c]
        return artifacts

class PromptfooCISource:
    """promptfoo/deepeval eval JSON pushed from CI to an ingest endpoint, OR polled job artifact.
    Reuses app.ingest.parse_eval_run EXACTLY — zero new normalization."""
    name = "promptfoo_ci"
    def fetch(self, conn) -> list[RawEvidence]:
        raw = pull_artifact(conn.config["ci_run_url"], conn)   # bytes/str
        ev = parse_eval_run(raw)                               # existing parser
        return [RawEvidence(evidence_type="eval_run", content=ev.content,
                            collected_at=ev.collected_at, source_name=ev.source_name)]

# Isolation wrapper (ARQ task):
def run_ingestion(conn: IntegrationConnection):
    run = IngestionRun(org_id=conn.org_id, source=conn.type, idempotency_key=conn.config.get("run_id"))
    try:
        src = get_source(conn.type)
        for raw in src.fetch(conn):
            store_artifact(conn.org_id, raw, run)              # writes EvidenceArtifact (immutable)
        run.status = "success"; run.items_ingested = len(...)
    except AdapterError as e:
        run.status = "failed"; run.error = str(e)[:500]        # NEVER re-raise
        conn.status = "degraded"
    finally:
        run.finished_at = dt.datetime.utcnow(); session.commit()
```

**Why these two (resolves deep-dive Q2):** GitHub App yields the *most* evidence types (model_card provenance, policy, eval artifacts, PR-approval governance signals) at the *lowest* auth friction (installation tokens, no per-user secrets, webhook-HMAC verified). promptfoo/deepeval reuses `parse_eval_run` verbatim — directly feeds Art. 15 / A.6 V&V with **zero** normalization cost. MLflow/HF/W&B poll is deferred: self-hosted servers ship with no auth (backend §2), a security risk we won't absorb in v0.2, and GitHub already captures model-card provenance at higher yield.

---

## 4. Migration Strategy (v0.1 engine → multi-tenant)

Keep the engine pure. Add a thin **service layer**; never pass `org_id` into `map_evidence`.

1. **Baseline:** `alembic revision --autogenerate` from the model skeletons above; first migration enables RLS in a separate `enable_rls` step.
2. **Service layer** `AssessmentService`:
   - `load_evidence(org_id)` → queries `EvidenceArtifact` (RLS-scoped automatically), converts each `raw_payload` → `Evidence` pydantic using the existing `ingest` parsers.
   - `assess(org_id, today=None)` → calls `map_evidence(evidence, today=today)` (UNCHANGED function) → writes `ControlMapping` rows (replacing prior mappings for the same catalog version) + a `ReportSnapshot` with `manifest_hash = sha256(concat(sorted content_hashes))`.
   - Determinism preserved (backend §5.3): non-determinism lives only in *fetching* inputs, which are snapshotted as immutable artifacts — a report is always reproducible from stored evidence.
3. **Engine stays the system of record** (ml-research §0): ML proposals (evidence→control suggestion, extraction) land in a separate `evidence_suggestions` table **behind `ACTREADY_PROVIDER` (default off)** — never mutate `control_mappings`. Backend provides the storage hook; ML features are the ML epic's scope.
4. **Live re-assessment** is triggered by ARQ on each successful `IngestionRun`, or on-demand via `POST /v1/assess`.

---

## 5. Deferred List (with entry trigger)

- **Temporal** — when ingestion becomes long-running/multi-step and must survive crashes mid-pipeline without duplicate side effects (backend §1.5). ARQ is fine until then.
- **WorkOS / Clerk SSO** — when the first enterprise SSO/SCIM deal appears. `get_principal` seam makes the swap local (backend §1.1).
- **Stripe Billing** — after PLG validates paid conversion. v0.2 ships `plan` field + feature gates with no charges; Checkout/Portal/webhooks land in v0.3 (backend §1.4, deep-dive Q7).
- **MLflow / HuggingFace / W&B connectors** — v0.3, behind an auth-fronted tracking server (security prerequisite).
- **OpenLineage, PagerDuty / incident.io webhooks** — v0.3 (incident_log from post-mortems).
- **Per-obligation freshness (Art. 73 event-driven)** — v0.3, needs control-metadata schema extension (deep-dive Q4).
- **Provider/Deployer role scoping** — v0.3 (deep-dive Q5).
- **Multi-workspace, auditor dashboards, Trust Center page** — v0.4 (roadmap; frontend §1f).

---

## 6. Backend v0.2 Tickets (by epic)

### E1 — Auth & DB Foundation
1. **E1.1 `get_principal` dependency + PyJWT issuance** — *AC:* `POST /v1/auth/login` returns JWT; protected routes reject missing/expired/`tenant_id`-mismatched tokens; token has `sub, tenant_id, exp`. *Effort: M.*
2. **E1.2 SQLAlchemy 2.0 engine + Alembic baseline** — *AC:* `alembic upgrade head` creates all tables on a fresh Postgres; CI runs migrations. *Effort: M.*
3. **E1.3 RLS policies + transaction-local GUC** — *AC:* `app_user` role cannot read rows outside `current_setting('app.tenant_id')`; `SET LOCAL` hook fires per request via SQLAlchemy event; cross-tenant read test fails. *Effort: L.*
4. **E1.4 Org/User/Membership + signup** — *AC:* signup creates org+owner membership; `viewer` role exists; unique membership enforced. *Effort: M.*

### E2 — Evidence Persistence & Engine Service
5. **E2.1 `EvidenceArtifact` immutable store + trigger** — *AC:* UPDATE/DELETE on artifacts blocked by DB trigger; `content_hash` computed from canonical JSON; `/verify` recomputes & compares. *Effort: M.*
6. **E2.2 `AssessmentService.assess`** — *AC:* loads org artifacts via RLS, calls `map_evidence` unchanged, writes `ControlMapping` + `ReportSnapshot` with `manifest_hash`; reproducible from stored evidence. *Effort: L.*
7. **E2.3 `ControlMapping` recompute + catalog version pin** — *AC:* mappings replaced per `catalog_version`; `report_snapshots.catalog_version` pointer stored. *Effort: S.*
8. **E2.4 `IngestionRun` idempotency** — *AC:* duplicate `idempotency_key` is a no-op; `status` + truncated `error` persisted. *Effort: S.*

### E3 — Integrations (GitHub App + promptfoo/deepeval)
9. **E3.1 `EvidenceSource` Protocol + isolation wrapper** — *AC:* `run_ingestion` catches `AdapterError`, writes failed run, never re-raises; aggregate report uses only successful runs. *Effort: M.*
10. **E3.2 GitHub App auth + webhook verification** — *AC:* installation token minted from `APP_ID`+`PRIVATE_KEY`; `X-Hub-Signature-256` HMAC validated before trust. *Effort: L.*
11. **E3.3 GitHubSource.fetch (model card, policy, eval artifact)** — *AC:* returns `RawEvidence` for the 3 types; maps to existing parsers; covered by unit tests with mocked API. *Effort: M.*
12. **E3.4 promptfoo/deepeval CI push ingest endpoint** — *AC:* `POST /v1/ingest/eval` accepts eval JSON, calls `parse_eval_run`, stores immutable artifact; reuses parser exactly. *Effort: S.*
13. **E3.5 `IntegrationConnection` encrypted creds** — *AC:* `creds_encrypted` stored via envelope encryption; plaintext never logged; `status` reflects health. *Effort: M.*

### E4 — Report Export & Share
14. **E4.1 Jinja2 HTML render + WeasyPrint PDF** — *AC:* `render_html(report)` → `write_pdf()`; deterministic output byte-for-byte for same input. *Effort: M.*
15. **E4.2 Versioned `report_snapshots` + diff** — *AC:* two snapshots yield a delta of controls whose status changed; history queryable. *Effort: M.*
16. **E4.3 Signed, revocable share link** — *AC:* `POST /v1/reports/{id}/share` issues short-`exp` JWT + `share_links` row; auditor read-only view works; revoke flips `revoked`. *Effort: M.*

### E5 — Reliability & Observability
17. **E5.1 Per-source health endpoint** — *AC:* `GET /v1/tenant/{id}/integrations` returns `connected|degraded(N)|disconnected` + last_sync. *Effort: S.*
18. **E5.2 ARQ worker + job enqueue** — *AC:* successful `IngestionRun` enqueues `assess`; worker boots in docker-compose; failing job retries with backoff. *Effort: M.*
19. **E5.3 OpenTelemetry metrics (ingest latency, failure count, evidence age)** — *AC:* metrics emitted; alert on 3 consecutive failures. *Effort: M.*

### E6 — Infra & Migration
20. **E6.1 docker-compose (Postgres+Redis+API+worker)** — *AC:* `make up` brings a working local stack; runs migrations + seeds a demo org. *Effort: M.*
21. **E6.2 v0.1→v0.2 migration script (file upload → artifact)** — *AC:* existing `POST /assess` multipart inputs persist as `EvidenceArtifact` rows for the calling org. *Effort: M.*
22. **E6.3 Catalog versioning + Omnibus dates as data** — *AC:* obligations file carries `version` + deferred-date fields; report pins version; no hardcoded law dates in code. *Effort: S.*

**Totals:** ~6 L, 11 M, 5 S. Sequenced E1→E2→E3→E4→E5/E6 in parallel. This turns ActReady from a single-tenant CLI into a tenant-aware, continuously-fed, auditor-trustworthy service while keeping the deterministic engine intact.
