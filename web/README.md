# ActReady — Frontend (v0.2)

The ActReady web app: a tenant-scoped SPA that turns the deterministic readiness
engine's output into a legible, actionable, auditor-exportable scorecard.

**Stack:** Vite · React 18 · TypeScript · Tailwind (shadcn-style tokens) · TanStack Query ·
React Router · Zustand · Recharts · Zod · Vitest.

> Built against the API contract in `docs/planning/frontend-plan.md` §2 — the backend
> (`api/`) is developed in parallel, so the frontend talks to a well-defined contract.

## Quick start

```bash
cd web
cp .env.example .env        # VITE_API_BASE defaults to /api
npm install
npm run dev                 # http://localhost:5173
```

Point `VITE_API_BASE` at the running backend if it isn't behind the same origin:

```bash
# .env
VITE_API_BASE=http://localhost:8000/api
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm run build` | Type-check (`tsc -b`) + production build |
| `npm run typecheck` | `tsc --noEmit` (project build, no emit) |
| `npm test` | Vitest unit/component tests |
| `npm run lint` | oxlint |

## Env

| Var | Default | Meaning |
| --- | --- | --- |
| `VITE_API_BASE` | `/api` | Base URL every API call is prefixed with |

## Routes

| Path | Screen | Contract |
| --- | --- | --- |
| `/auth/login`, `/auth/register` | Auth shell (AUTH-3) | `POST /auth/login`, `/auth/register` |
| `/readiness` | Readiness Scorecard (FE-1) | `GET /api/readiness` |
| `/controls` | Control Library (FE-2) | `GET /api/controls` |
| `/controls` + row → drawer | Detail Drawer (FE-3) | `GET /api/controls/:id` |
| `/evidence` | Evidence Vault (INT-4) | `POST /api/evidence` + poll `GET /api/evidence/:id` |
| `/export` | Audit / Export (RPT-2) | `GET /api/report?format=markdown\|json\|pdf` |

## Design tokens (FE-4)

Single blue accent (`--primary`), otherwise light/dense dev-tool styling. The only
"loud" colors are semantic status hues: satisfied = green, partial = amber,
missing = red (see `src/index.css` and `tailwind.config.js`).

## State ownership

- **Zustand** holds only thin UI state: the JWT (`store/auth`), control-library
  filters + selected control for the drawer (`store/ui`).
- **TanStack Query** owns all server data and the ingest-status polling loop.

## Notes for the parallel backend agents

- The API client injects `Authorization: Bearer <jwt>` on every request and treats
  `401` as "session expired" (forces re-login).
- There is no `GET /api/evidence` **list** endpoint in the contract; the vault tracks
  uploaded artifact ids client-side and polls each via `GET /api/evidence/:id`.
- PDF export calls `GET /api/report?format=pdf` (backend capability ships in v0.2);
  the button is intentionally present but the frontend UI work is deferred to P1.
