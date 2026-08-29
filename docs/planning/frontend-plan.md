# ActReady — Frontend v0.2 Scope & Plan

**Date:** 2026-08-29 · **Author:** Planning agent · **Status:** Scope-locked for v0.2 build
**Audience:** 4-person ActReady team (React-strong). Depends on the v0.2 backend contract defined in `docs/backend-research.md`.
**Grounded in:** `docs/frontend-research.md` (FR), `docs/research-deep-dive.md` (RD), `docs/backend-research.md` (BK), `docs/ml-research.md` (ML), and the v0.1 engine source (`api/app/mapper.py`, `api/app/models.py`, `api/app/report.py`).

---

## 1. v0.2 Frontend Scope Decision

The frontend's job is to make the engine's deterministic output **legible, actionable, and auditor-exportable** — not to become a live monitoring console. I resolve each open question from FR §5 and accept/defer every P0/P1/P2 item.

### Open-question resolutions (FR §5, RD §7, BK §6)

| # | Open question | Resolution | Rationale |
|---|---|---|---|
| 1 | Auth & multi-user | **Accept lightweight email/password auth + single workspace** for v0.2. JWT carries `sub`/`tenant_id`/`exp` behind a `get_principal` seam (BK §1.1). Multi-workspace deferred to v0.4. | Matches roadmap; no sales-led SSO needed at PLG wedge. |
| 2 | Persistence layer | **Postgres + SQLAlchemy 2.0/Alembic, RLS tenant isolation** (BK §1.2). Snapshots power the sparkline. | Required for diffable reports and readiness-over-time. |
| 3 | Evidence storage | **Metadata + bytes + sha256 content hash** (`evidence_artifacts` immutable rows, BK §3.2). S3/R2 optional for large bytes; hash gives auditor trust. | Tamper-evidence is the trust moat. |
| 4 | Integrations priority | **GitHub App + manual upload for v0.2**; MLflow/promptfoo/pagerduty deferred (BK MVP). | Highest signal, lowest auth friction. |
| 5 | Scoring display | Show **readiness score (0–100)** as hero; surface `partial` separately as 0.5-weighted but never in the headline as "pass." Framework % bars (Trustible-style) are computed client-side from control counts. | FR §5.5 asks exactly this; engine emits `readiness_score`. |
| 6 | Report export fidelity | **Markdown + JSON in v0.2** (engine-native, `render_markdown`). **PDF deferred to v0.3** (server-side WeasyPrint per BK §4.1). | Ships the loop without a print-engine dependency. |
| 7 | Free vs paid gating | A `plan` field on tenant (BK §1.4) gates: free = watermarked markdown summary + manual upload; paid = full export, secure share links, integrations. No Stripe UI in v0.2. | PLG wedge per RD §5. |
| 8 | REVIEW-COUNSEL surfacing | **Inline in the per-control drawer** (recommended in FR §5.8) with a distinct amber "needs legal review" callout. No separate queue in v0.2. | Keeps uncertain mappings visible at the point of decision. |

### P0 / P1 / P2 acceptance

**P0 — SHIP in v0.2 (the connect→score→gap→export loop):**
1. ✅ **Auth + workspace shell** — login, nav, app layout. Foundational.
2. ✅ **Readiness Scorecard / Overview** (FR §1a) — hero screen; proves value instantly.
3. ✅ **Control Library View** (FR §1b) — filter by `satisfied`/`partial`/`missing`; the daily driver.
4. ✅ **Per-Control Detail Drawer** (FR §1d) — obligation mapping, remediation hint, freshness, REVIEW-COUNSEL.
5. ✅ **Manual Upload → Evidence Vault (minimal)** (FR §1c) — upload model card / eval JSON / incidents; ingest status + linked control. **GitHub connector is a P1 fast-follow, not blocking.**
6. ✅ **Audit/Export View — Markdown + JSON** (FR §1e) — generate & download the gap report; PDF deferred.

**P1 — fast follow (end of v0.2 / v0.3):**
7. ⏭ **Integrations Page** — GitHub connector + MLflow; auto-sync states (FR §1f).
8. ⏭ **Readiness-over-time sparkline** — needs persistence/history (FR §1a, RD §7q9).
9. ⏭ **Share-with-auditor secure link** — read-only scoped view (FR Flow C; backend `/reports/{id}/share` per BK §4.3).

**P2 — later (v0.3+):**
10. ⏭ **Policy/Playbook Generator** (FR §1g; ML §1d — highest hallucination exposure, defer).
11. ⏭ **Audit comments/requests loop**, multi-workspace, dedicated auditor view (v0.4 roadmap).

**Net:** P0 delivers the full <5-min activation loop and the kill-criteria metric ("partner passes a buyer's review using ActReady output") with minimal new backend beyond auth + persistence + the 6 endpoints in §2.

---

## 2. Stack & API Contract

### Confirmed stack (FR §3)

- **Build:** Vite + React 18 + TypeScript.
- **Styling/UI:** Tailwind CSS + **shadcn/ui** (Radix primitives, CSS-variable theming — owned/editable in-repo) + **Zod** for client validation (mirrors the engine's pydantic contracts).
- **Charts:** Recharts (scorecard donut, framework bars, freshness strip, sparkline).
- **Server state:** TanStack Query (assessment polling, ingest status, report gen).
- **Routing:** React Router v6 (shell + protected routes).
- **Client state:** **Zustand** for thin UI state (active filters, drawer open control, selected framework) — avoids Redux weight; TanStack Query owns all server state.
- **API client:** `openapi-typescript` + `openapi-fetch` to generate a typed `Api` client from the backend's OpenAPI schema (`openapi.json`), so frontend and API **cannot drift**. Run `openapi-typescript ./openapi.json -o src/lib/api-types.ts` in a `postbuild`/CI step.

### How the frontend talks to the backend

The frontend is a **tenant-scoped SPA** that sends `Authorization: Bearer <jwt>` on every request. The v0.2 backend (BK §6) must expose these endpoints; the frontend assumes exactly this contract:

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| `POST` | `/auth/login` | Email/password → JWT | `{email, password}` | `{access_token, token_type:"bearer", tenant_id}` |
| `POST` | `/auth/register` | Signup → workspace | `{email, password, workspace_name}` | `{access_token, tenant_id}` |
| `GET` | `/api/readiness` | Hero scorecard | — | `ReadinessResponse` (below) |
| `GET` | `/api/controls` | Control library rows | `?status=satisfied\|partial\|missing&framework=iso42001\|eu_ai_act&q=` | `ControlItem[]` |
| `GET` | `/api/controls/:id` | Detail drawer | — | `ControlDetail` (below) |
| `POST` | `/api/evidence` | Manual upload | `multipart: file` (+ optional `control_id`) | `EvidenceArtifact` (ingest status) |
| `GET` | `/api/report` | Export | `?format=markdown\|json` | `text/markdown` or `GapReport` JSON |

### Contract shapes (derived from `mapper.py` / `models.py`)

```ts
// GET /api/readiness
interface ReadinessResponse {
  readiness_score: number;          // 0–100, engine: (satisfied + 0.5*partial)/total
  total: number;                    // controls assessed (39 ISO + 21 AI Act in catalog)
  satisfied: number; partial: number; missing: number;
  freshness_window_days: number;    // 180
  as_of: string;                    // ISO date
  frameworks: {                     // client-side % bars (FR §5.5)
    iso42001:  { satisfied:number; partial:number; missing:number };
    eu_ai_act: { satisfied:number; partial:number; missing:number };
  };
  stale_within_30d: number;         // freshness strip (FR §1a)
  last_assessed_at: string | null;  // timestamp of latest snapshot
}

// GET /api/controls
interface ControlItem {
  control_id: string;               // e.g. "A.6.3"
  control_name: string;
  framework: "iso42001" | "eu_ai_act";
  obligation_ids: string[];         // e.g. ["ART13"]
  status: "satisfied" | "partial" | "missing";
  evidence_count: number;
  evidence_age_days: number | null; // null = no evidence
  owner: string | null;
  remediation_hint: string;         // engine string, empty when satisfied
  review_counsel: boolean;          // uncertain mapping flag (FR §5.8)
}

// GET /api/controls/:id
interface ControlDetail extends ControlItem {
  obligations: { id:string; article:number; title:string; source_url:string }[];
  freshness: { collected_at:string|null; age_days:number|null; stale_in_days:number|null };
  linked_evidence: { id:string; type:string; source:string; collected_at:string }[];
  history: { status:string; changed_at:string }[];  // v0.2 diffable snapshots
}

// POST /api/evidence
interface EvidenceArtifact {
  id: string;
  evidence_type: "model_card"|"eval_run"|"incident_log"|"policy";
  source: string;                   // "manual:filename.yaml"
  ingest_status: "processing"|"ingested"|"failed";
  content_hash: string;             // sha256 (BK §3.2)
  collected_at: string;
  error?: string;
}
```

The `/api/readiness` and `/api/controls` responses are computed by the backend calling the **unchanged deterministic engine** (`map_evidence`) over persisted `evidence_artifacts` for the tenant (BK §1). Status semantics match `mapper.py`: `satisfied` = matching-type evidence within 180d; `partial` = exists but stale; `missing` = none. `remediation_hint` is the engine's exact string (empty when satisfied, "stale (N days old)" when partial).

---

## 3. Screen Specs (P0)

### 3.1 Auth + Workspace Shell
- **Layout:** Centered card login/register (shadcn `Card`, `Input`, `Button`); on success, redirect to `/readiness`. App shell = left `Sidebar` (Readiness, Controls, Evidence, Export) + top bar (workspace name, user menu, "Re-run" button).
- **Components:** `AuthForm`, `AppShell`, `Sidebar`, `TopBar`, `ProtectedRoute`.
- **Data:** `POST /auth/login|register` → store JWT in `Zustand` + `localStorage`.
- **States:** Loading (spinner on submit); empty N/A; error (`401` → inline "Invalid credentials", network → toast).

### 3.2 Readiness Scorecard / Overview (FR §1a)
- **Layout:** Hero `readiness_score` donut (Recharts) + delta vs last snapshot; two framework cards (ISO 42001, EU AI Act) with satisfied/partial/missing chip breakdown; "Gaps needing attention" worst-first list (status `missing`→`partial`, sorted) each linking to the control; freshness strip ("N controls stale in <30d"); "Last assessed" + "Re-run assessment" button.
- **Components:** `ScoreDonut`, `FrameworkCard`, `GapList`, `FreshnessStrip`, `RerunButton`.
- **Data:** `GET /api/readiness`. Worst-first gaps = `GET /api/controls?status=missing,partial` sorted by status.
- **States:** Loading (skeleton donut + bars); empty (no evidence yet → CTA "Upload your first artifact"); error (toast + retry; never blank screen — the Places-style "one bad input kills the page" bug BK §5 warns against).

### 3.3 Control Library View (FR §1b)
- **Layout:** Left rail framework tree (ISO 42001 Annex A groups A.2–A.10 → controls; EU AI Act Art. 9–15 → obligations). Top: status toggle chips (`satisfied|partial|missing|all`, multi-select), search box, sortable columns. Table rows: ID, name, obligations, status chip, evidence count, age, owner. Row click → drawer (3.4).
- **Components:** `FrameworkTree`, `StatusFilter`, `ControlTable`, `StatusChip`, `BulkActions` (assign owner / export subset — export subset is P1).
- **Data:** `GET /api/controls` with filter/sort query params (server-filtered for correctness).
- **States:** Loading (table skeleton); empty (no controls match filter → "All clear / adjust filter"); error (row-level: if one framework fails, show others + a degraded banner, per BK §5.1 isolation).

### 3.4 Per-Control Detail Drawer (FR §1d)
- **Layout:** Right-side `Sheet` (shadcn). Header: ID + name + status chip + owner. Sections: **Obligation mapping** (chips linking to EUR-Lex `source_url`), **Remediation hint** (copy-pasteable engine string), **Freshness** (180-day clock "collected 45d ago, stale in 135d"), **Linked evidence** list, **REVIEW-COUNSEL** amber callout when `review_counsel=true`, **History** (status over time).
- **Components:** `ControlDrawer`, `ObligationLinks`, `RemediationHint`, `FreshnessMeter`, `EvidenceList`, `ReviewCounselBadge`.
- **Data:** `GET /api/controls/:id`.
- **States:** Loading (skeleton rows); empty (no linked evidence → show remediation hint prominently); error (drawer shows inline error, list behind stays usable).

### 3.5 Evidence Vault — Manual Upload (FR §1c, minimal)
- **Layout:** List of `EvidenceArtifact` cards (filename/source, type chip, ingest status, collected date, freshness state). Upload zone (drag-drop + file picker) accepting `.yaml/.yml/.json/.csv` mapping to the 4 engine types. Failed-ingest callout with reason + "re-upload". Provenance: show `content_hash` (copyable) for tamper-evidence.
- **Components:** `UploadDropzone`, `EvidenceCard`, `IngestStatusBadge`, `HashChip`.
- **Data:** `POST /api/evidence` (multipart) → poll `GET /api/evidence/:id` until `ingested`/`failed`; on success, refetch `/api/readiness` + `/api/controls`.
- **States:** Uploading (progress); processing (spinner, poll); failed (red callout + retry); success (green → auto-updates scorecard). Stale detection from `collected_at`.

### 3.6 Audit / Export View — Markdown + JSON (FR §1e)
- **Layout:** Config (frameworks scope, format toggle Markdown/JSON, include-expired-evidence); live preview pane (rendered scorecard + gaps + citations, mirroring `render_markdown`); completeness check ("X of Y obligations covered — 79% complete"); one-click download; free-tier watermarked summary note.
- **Components:** `ReportConfig`, `ReportPreview`, `DownloadButton`, `CompletenessBar`.
- **Data:** `GET /api/report?format=markdown|json`.
- **States:** Generating (skeleton preview); empty (no evidence → "nothing to export yet"); error (toast). Share-link is P1.

---

## 4. Design System — PLG Dev-Tool Tokens

Goal: **clean, light, high-density, dev-tool feel** — Vanta's one-hero-number legibility without OneTrust's enterprise density (FR §3). Semantic status colors are the only accent.

### Color tokens (CSS variables in `index.css`, shadcn theming)
```
--background: 0 0% 100%        /* white app */
--foreground: 222 47% 11%      /* near-black slate */
--muted: 210 40% 96%           /* panel bg */
--muted-foreground: 215 16% 47%/* secondary text */
--border: 214 32% 91%
--primary: 221 83% 53%         /* ActReady blue — single restrained accent */
--ring: 221 83% 53%

/* semantic status — the only "loud" colors */
--status-satisfied: 142 71% 45%   /* green  */
--status-partial:   38 92% 50%     /* amber  */
--status-missing:   0 72% 51%      /* red    */
--status-satisfied-fg / -partial-fg / -missing-fg: white
```
Status maps to engine `status`: `satisfied=green`, `partial=amber`, `missing=red` (FR §1b chips; mirrors the engine's worst-first ordering). Chips use `bg-status-*/text-white`, 2px radius, 11px uppercase label.

### Typography
- Font: `Inter` (UI) + `JetBrains Mono` (control IDs, hashes, scores). Base 14px / line-height 1.5. Hero score 48px bold tabular-nums. Section titles 13px uppercase tracking-wide muted.

### Spacing & density
- 4px base scale (`--space-1`…`--space-8`). App content max-width 1200px, 16px gutters. Table row height 44px (dense, GRC users *want* data — FR §3). Radius `0.5rem` cards, `0.375rem` chips/inputs. Subtle 1px borders, no heavy shadows.

### shadcn theming
- `components.json` with `style: "new-york"`, `cssVariables: true`. All status colors flow through `tailwind.config` `extend.colors` mapped to the CSS vars so `bg-status-partial` works. Dark mode deferred (read-only scorecard on mobile is P1; authoring is desktop-only per FR §3).

---

## 5. Activation & Share Flows

### Flow A — Activation (signup → first score <5 min) (FR §4 A)
1. **Register** (`/auth/register`) → workspace + JWT created.
2. **Onboarding wizard** (one screen): "What are you preparing for?" → pre-selects framework scope (RD §5 ICP: enterprise review / ISO 42001 / EU AI Act).
3. **Connect first source** — fastest path is **Upload a model card YAML** or **Paste eval JSON** (3.5). One click, no sales call.
4. On upload → `POST /api/evidence` → backend re-runs engine → redirect to **Scorecard** with computed `%` + worst-first gaps.
5. **Aha copy:** "You're 41% ready for ISO 42001. Here are your 3 biggest gaps." CTA to close top gap (opens 3.4).
6. **Share prompt:** offer watermarked markdown report (free) — seeds Flow C.
*Target: signup → score < 5 min, zero human assistance (Delve/Trustible narrative, self-serve — FR §4).*

### Flow C — Share-with-auditor (P1 secure link; v0.2 manual export)
- v0.2: user downloads Markdown/JSON from 3.6 and emails it. The **secure read-only scoped link** (`/reports/{id}/share`, BK §4.3) is **P1** — when it lands, the auditor opens a read-only scorecard + evidence vault with traceable dated artifacts and **no auto-asserted conclusions** (the Delve-lessons-learned guardrail, RD §3 / ML §0). Each control links to its linked dated evidence; watermark-free for paid tiers.

---

## 6. Tickets (GitHub-issue-shaped, grouped by epic)

Effort: **S** = <0.5d, **M** = 0.5–2d, **L** = 2–5d. All assume the backend contract in §2.

### Epic A — Foundation & Tooling
- **A1. Scaffold Vite+React+TS app** — *AC:* `npm create vite` done, Tailwind + path aliases, `npm run dev` serves blank shell. Effort S.
- **A2. Install & configure shadcn/ui + Recharts + TanStack Query + Zustand + React Router + Zod** — *AC:* `components.json` new-york style; `Button/Card/Input/Sheet/Table` present; deps in `package.json`. Effort S.
- **A3. OpenAPI client generation pipeline** — *AC:* `openapi-typescript` runs against backend `openapi.json` → `src/lib/api-types.ts`; `openapi-fetch` `Api` instance with bearer injection; CI step fails on drift. Effort M.
- **A4. Design tokens & shadcn theme** — *AC:* `index.css` defines status colors + Inter/JetBrains; `tailwind.config` maps `status-*`; Storybook-free visual check on a tokens page. Effort M.

### Epic B — Auth & Shell
- **B1. Auth API client + token store** — *AC:* `POST /auth/login|register` wired; JWT in Zustand+localStorage; 401 auto-logout. Effort M.
- **B2. Login/Register screens** — *AC:* validated forms (Zod), error states, redirect to `/readiness`. Effort M.
- **B3. App shell + protected routes + sidebar** — *AC:* `ProtectedRoute` gates all app routes; sidebar nav + topbar with workspace/user; "Re-run" button stub. Effort M.

### Epic C — Readiness Scorecard
- **C1. Readiness API hook + donut** — *AC:* `useReadiness` (TanStack Query) → `ScoreDonut` renders `readiness_score` 0–100 with delta vs last snapshot. Effort M.
- **C2. Framework cards + freshness strip** — *AC:* ISO/EU AI Act cards with satisfied/partial/missing chips; "N stale <30d" strip from `stale_within_30d`. Effort M.
- **C3. Worst-first gaps list** — *AC:* `GET /api/controls?status=missing,partial` sorted; each row links to drawer; empty/loading/error states. Effort M.
- **C4. Re-run assessment action** — *AC:* triggers backend re-assess; refetches readiness+controls; loading + optimistic UI. Effort S.

### Epic D — Control Library
- **D1. Controls table + status filter** — *AC:* `GET /api/controls` server-filtered by `status` toggles + `q` search; sortable columns; status chips. Effort M.
- **D2. Framework tree rail** — *AC:* ISO 42001 A.2–A.10 + EU AI Act Art. 9–15 tree; click filters table by framework. Effort M.
- **D3. Row → drawer open wiring** — *AC:* row click opens `ControlDrawer` with `:id`; Esc/overlay close; deep-linkable URL. Effort S.

### Epic E — Control Detail Drawer
- **E1. Drawer layout + obligation mapping** — *AC:* header chip+owner; obligation chips link to `source_url` (EUR-Lex). Effort M.
- **E2. Remediation hint + freshness meter** — *AC:* shows engine `remediation_hint`; 180-day clock "collected Xd ago, stale in Yd". Effort M.
- **E3. Linked evidence + history + REVIEW-COUNSEL** — *AC:* lists `linked_evidence`; renders `history` statuses; amber `ReviewCounselBadge` when `review_counsel=true`. Effort M.

### Epic F — Evidence Vault (Manual Upload)
- **F1. Upload dropzone + type mapping** — *AC:* drag-drop/.yaml/.json/.csv → `POST /api/evidence` multipart; maps suffix to engine type. Effort M.
- **F2. Ingest status polling + cards** — *AC:* poll until `ingested`/`failed`; `EvidenceCard` shows type/status/collected/freshness; failed → retry. Effort M.
- **F3. Provenance hash + post-upload refetch** — *AC:* show `content_hash` (copyable); on success refetch readiness+controls so score updates live. Effort S.

### Epic G — Audit / Export
- **G1. Report config + Markdown/JSON preview** — *AC:* scope + format toggle; `GET /api/report` rendered in preview pane mirroring `render_markdown`. Effort M.
- **G2. Download + completeness bar + watermark note** — *AC:* one-click download; "X/Y obligations covered — Z% complete"; free-tier watermarked-summary copy. Effort M.

### Epic H — P1 Fast-Follow (tracked, not in v0.2 cut)
- **H1. GitHub connector (integrations page)** — *AC:* GitHub App auth + webhook ingest of eval/policy evidence; per-source health (BK §5.2). Effort L.
- **H2. Readiness-over-time sparkline** — *AC:* chart from `report_snapshots` history. Effort M.
- **H3. Share-with-auditor secure link** — *AC:* `POST /reports/{id}/share` → expiring read-only link; auditor read-only view. Effort L.
- **H4. PDF export (server-side WeasyPrint)** — *AC:* `GET /api/report?format=pdf` returns PDF. Effort M.

---

## Summary of decisions
- **P0 = 6 screens** deliver the full activation loop; **P1 = 3** (GitHub connector, sparkline, share link); **P2 = 2** (policy gen, auditor comments).
- Stack **confirmed** with Zustand (not Redux) + `openapi-typescript` client generation to kill API drift.
- Backend must expose **7 endpoints** (§2) computed by calling the **unchanged deterministic engine** over persisted evidence.
- Design = **light, dense, single-blue-accent dev tool** with green/amber/red semantic status — explicitly *not* enterprise GRC.
- All 8 frontend open questions resolved; ML/advisory features (risk-tier, NL drafting) correctly **deferred** per ML §6 to keep the deterministic core the system of record.
