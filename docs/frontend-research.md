# ActReady — Frontend & Product Research Brief

**Date:** 2026-08-29 · **Author:** Frontend/Product Research Agent · **Status:** Draft for planning phase
**Scope:** Web UI surface map, competitor teardowns, design direction, UX flows. Research only — no code.
**Audience:** 4-person ActReady team (React-strong). Buyers are AI-native startups doing enterprise security reviews.

---

## 0. Context from the v0.1 engine

Before designing screens, anchor on what the engine already produces. v0.1 (per `README.md`, `docs/research-brief.md`) is a **deterministic evidence compiler**:

- Ingests `model_card.yaml`, `eval_run.json`, `incidents.csv` (pluggable normalizer layer).
- Maps them against versioned catalogs: **ISO/IEC 42001 Annex A (condensed)** and **EU AI Act Articles 9–15**.
- Scores each control: **satisfied** (matching evidence within 180 days), **partial** (stale evidence), **missing** (none). Obligations roll up from controls; `readiness = (satisfied + 0.5·partial) / total`.
- Outputs **markdown** (scorecard table, worst-first gaps, citations) and **GapReport JSON** via `POST /assess`. No web UI yet.
- Roadmap: v0.2 (SOC 2 / NIST AI RMF catalogs, deep-link rendering, diffable reports), v0.3 (CI integration, freshness policies), v0.4 (multi-workspace, auditor read-only views, export to Vanta/Drata-style evidence packets).

**Design implication:** the product's core value is *a scored, dated, attributable evidence trail* — not a monitoring daemon. The UI should make that score legible, let users close gaps, and produce auditor-acceptable artifacts. Avoid the "always-on dashboard you live in" framing the research brief explicitly rejects.

---

## 1. PRODUCT UI SURFACE ANALYSIS

Seven core screens an AI-governance dashboard needs. For each: purpose + key UI elements.

### (a) Readiness Scorecard / Overview
**Purpose:** The "are we audit-ready?" landing screen. Answers in one glance: overall readiness %, progress per framework, and what's on fire this week.

**Key elements:**
- Hero metric: overall readiness score (big number, 0–100) with delta vs. last run (trend line).
- Framework cards: ISO 42001 and EU AI Act side-by-side, each with its own % and a satisfied/partial/missing chip breakdown.
- "Gaps needing attention" panel: worst-first list (mirrors the engine's worst-first gap output), each row linking to its control.
- Freshness strip: count of controls whose evidence goes stale in <30 days (the 180-day clock).
- "Last assessed" timestamp + "Re-run assessment" button.
- Sparkline of readiness over time (needs v0.2 diffable reports — UNVERIFIED whether historical snapshots are stored; assume yes for v0.2+).

**Reference pattern:** Vanta's overview dashboard does exactly this for security controls — framework progress, top-failing tests, per-owner task completion — and it works because the at-a-glance number anchors every downstream decision ([vanta.com/products/automated-compliance](https://www.vanta.com/products/automated-compliance)).

### (b) Control Library View
**Purpose:** The browsable catalog of every control/obligation, filterable by status. This is where users live day-to-day.

**Key elements:**
- Left rail: framework tree (ISO 42001 Annex A clauses → controls; EU AI Act Art. 9–15 → obligations).
- Status filter: `satisfied | partial | missing` toggles + "all". Multi-select.
- Search box (control ID, keyword, obligation text).
- Table/list rows: control ID, title, mapped obligation(s), status chip (green/amber/red), evidence count, last-refreshed date, owner.
- Sortable by status, freshness, framework.
- Bulk actions: assign owner, export subset.
- Row click → opens the per-control detail drawer (1e).

**Why this matters:** Trustible's control library ("map controls once, satisfy every framework") is the closest analog and the differentiator they lead with ([trustible.ai](https://trustible.ai)). ActReady's edge is that control status is *derived from real artifacts*, not manually asserted.

### (c) Evidence Vault
**Purpose:** Show each control's linked evidence artifacts, with upload + auto-ingest status. The "show me" room an auditor walks into.

**Key elements:**
- Per-control tab or filtered view of evidence items.
- Each evidence artifact card: filename/source, type (model card / eval run / incident log / policy doc), linked control(s), ingest status (`ingested | processing | failed`), collection date, freshness state (within 180 days / stale).
- Upload affordance: drag-drop + "connect source" (GitHub repo, MLflow run, file).
- Auto-ingest status: for connected integrations, poll state ("MLflow run #412 synced 2h ago").
- Failed-ingest callout with reason + "re-upload" action.
- Evidence provenance: hash/version so artifacts are tamper-evident (ties to auditor-trust goal in research brief).

**Reference:** Vanta's evidence collection shows the model — automated tests feed evidence, documents stored, status tracked ([help.vanta.com — Evidence Collection](https://help.vanta.com/en/collections/12734665-evidence-collection)). ActReady should show *which artifact satisfied which control*, which incumbents blur.

### (d) Per-Control Detail Drawer
**Purpose:** The deepest single view — obligation mapping, remediation hint, freshness. Opens from Control Library or Evidence Vault.

**Key elements:**
- Header: control ID + title + status chip + owner.
- **Obligation mapping:** which ISO 42001 clause(s) and EU AI Act article(s) this satisfies; link out to the source text (EUR-Lex citations already in engine).
- **Remediation hint:** what evidence would move `missing → partial → satisfied`. Concrete, copy-pasteable ("upload a model card YAML with field `data_governance` set").
- **Freshness:** 180-day clock visualization, "collected 45 days ago, stale in 135."
- **Linked evidence:** list of artifacts currently satisfying it.
- **REVIEW-COUNSEL flag:** if the mapping is uncertain, surface the disclaimer inline (the engine already flags these).
- **History:** change log of status over time (v0.2 diffable reports).

### (e) Audit / Export View
**Purpose:** Generate an auditor-acceptable report (PDF/markdown). The money screen — output an external party trusts.

**Key elements:**
- Report config: select framework(s), scope (all controls or a date range / subset), format (Markdown / PDF / JSON), include-expired-evidence toggle.
- Live preview pane: rendered scorecard + gaps + citations.
- "Watermark free" / branding toggle for paid tiers (free tier watermarked summary per GTM plan).
- One-click export; download + "share secure link" (feeds the share-with-auditor flow in §4).
- Completeness check: "X of Y obligations covered — report is 79% complete."

**Why critical:** Trustible markets "audit-ready evidence at every step, automatically" with framework % bars (EU AI Act 88%, NIST 94%, ISO 42001 79%) right on the dashboard ([trustible.ai](https://trustible.ai)) — buyers expect a one-click exportable artifact, not a screenshot.

### (f) Integrations Page
**Purpose:** Connect the sources the engine ingests — GitHub, MLflow, promptfoo/deepeval, incident trackers — so evidence flows automatically instead of manual upload.

**Key elements:**
- Catalog of connectors with status (connected / available / coming soon): GitHub (model cards in repo), MLflow (eval/run metadata), promptfoo/deepeval (eval JSON), incident CSV source, cloud storage.
- OAuth/API-key connect flow per integration.
- Per-connector: last-sync time, items ingested, error state.
- "Test connection" + sync-now button.

**UNVERIFIED:** The repo roadmap (README) does not yet list GitHub/MLflow connectors explicitly — integrations first appear as a UI surface in this brief and in the v0.4 "export to Vanta/Drata-style evidence packets" note. Treat the Integrations page as a v0.3+ surface; v0.2 should at minimum support manual upload + a GitHub-repo-connected model-card ingest.

### (g) Policy / Playbook Generator
**Purpose:** Turn the gap report into draft governing documents (model card template, AI-use policy, Article 13 instructions-for-use) the team can adopt. Moves ActReady from "compiler" toward "governance OS."

**Key elements:**
- Template picker: model card, AI policy, risk-assessment template, EU AI Act Art. 13 instructions-for-use doc.
- Inputs: pull from current evidence + gaps to pre-fill.
- Generated doc preview (markdown) with "copy / download / save to Evidence Vault."
- Editable before save.

**UNVERIFIED / forward-looking:** No generator exists in v0.1. This is the natural v0.3+ extension and aligns with OneTrust's "auto-generate System Description / Statement of Applicability" pattern ([vanta.com/features](https://www.vanta.com/features) for the Vanta analog; OneTrust markets similar doc-auto-gen). Mark as a candidate, not a commitment.

---

## 2. COMPETITOR UI TEARDOWNS

Five competitors, real UI/UX approach from their marketing/screenshots + public demos. What's good, what's heavy that a nimble PLG product can beat.

### Vanta — [vanta.com](https://www.vanta.com)
- **Approach:** Polished, consumer-grade trust-management dashboard. Overview with framework progress, top-failing automated tests, per-owner task completion bars (HR 50%, IT 100%…), test-status board ("20% OK, 39 needing attention, last refreshed 3 min ago"). Trust Center public pages. Audit product: evidence status tracking, auditor access scoping, "only Vanta gives auditors test source data — no screenshots required."
- **Good:** Best-in-class activation (connect integrations → see first score fast), continuous-control-monitoring mental model, auditor collaboration built in. The at-a-glance score is the gold standard.
- **Heavy/clunky to beat:** Enterprise GRC pricing and sales-led motion; SOC 2 / ISO 27001 *infrastructure* controls only — **does not parse ML artifacts** (eval JSON, model cards) into Article 11 documentation. That blind spot is ActReady's wedge (research brief §3: "Vanta automates infrastructure controls… does not parse your eval exports").
- **Cite:** [automated-compliance](https://www.vanta.com/products/automated-compliance), [audit](https://www.vanta.com/products/audit), [features](https://www.vanta.com/features).

### Delve — [delve.co](https://delve.co)
- **Approach:** AI-agent compliance automation, "TurboTax-style" onboarding, white-glove Slack support, very wide framework catalog including ISO 42001 + EU AI Act natively. MIT-founded, $32M Series A.
- **Good:** Speed-to-compliance narrative, AI-collects-evidence → humans-validate → auditor-examines three-layer flow, sub-5-minute support. Strong PLG-adjacent onboarding story.
- **Heavy/clunky / cautionary:** **Credibility crisis** — a 2025–2026 investigation documented Delve auto-generating passing evidence and draft auditor conclusions *before* clients provided anything, violating AICPA AT-C 205 independence ([systima.ai investigation](https://systima.ai/blog/delve-compliance-fraud-eu-ai-act-conformity-assessment); LinkedIn post acknowledging they "will no longer automate these parts"). **ActReady's deterministic, artifact-traceable, not-legal-advice posture is the explicit antidote** — never auto-assert compliance without a linked dated artifact.
- **Cite:** [delve.co/learn](https://delve.co/learn/grc/ai-transforming-grc-compliance), LinkedIn, Systima investigation.

### OneTrust — [onetrust.com/solutions/ai-governance](https://www.onetrust.com/solutions/ai-governance/)
- **Approach:** Enterprise "AI-Ready Governance Platform." AI inventory/discovery, risk tiering by use case, continuous monitoring, programmatic guardrails, "single pane of glass," 200+ connectors, role/attribute-based access, customer-managed keys.
- **Good:** Most complete capability map; "defensible decision dataset" with decision lineage; stack-neutral governance; enterprise security posture.
- **Heavy/clunky to beat:** The quintessential enterprise suite — demo-gated, form-to-tour, priced for Global 2000, UI is dense config-and-workflow surfaces. A 10–500-person AI-native team finds it overkill. **ActReady beats on speed, ML-artifact-native ingestion, and PLG pricing** — OneTrust is built for the CISO's program office, not the founding ML engineer who got handed compliance.
- **Cite:** [ai-governance](https://www.onetrust.com/solutions/ai-governance/), [platform](https://www.onetrust.com/platform/), [enterprise-scale](https://www.onetrust.com/why-onetrust/ai-governance-at-enterprise-scale/).

### Holistic AI — [holisticai.com](https://www.holisticai.com)
- **Approach:** "Identify → Protect → Enforce" AI governance. Auto-discovers models/agents/APIs across AWS, Azure, GitHub, Databricks (20+ integrations), 40+ bias/safety/security tests, Guardian/Sentinel agents, framework assessments (EU AI Act, NIST, ISO 42001), audit trails + on-demand reports.
- **Good:** Strong technical/ML discovery and testing depth; continuous assurance dashboards; enterprise-ready infra support.
- **Heavy/clunky to beat:** Broad enterprise AI-risk suite with agent runtime enforcement — far heavier than ActReady's "compile evidence you already produce" scope. Their discovery scans your whole stack; ActReady ingests what you point it at. **Narrower scope = faster time-to-first-score and cheaper to run.**
- **Cite:** [holisticai.com](https://www.holisticai.com), [ai-governance-platform](https://www.holisticai.com/ai-governance-platform).

### Trustible — [trustible.ai](https://trustible.ai)
- **Approach:** "Purpose-built AI governance platform." Rules-based (not black-box) risk scoring, control mappings across 10+ frameworks mapped once, AI monitoring/alerts, framework % bars on dashboard (EU AI Act 88%, NIST 94%, ISO 42001 79%), 90-day "live" motion, Gartner MQ mention.
- **Good:** Cleanest "map controls once → satisfy every framework" UX; transparent rules engine (auditor-friendly); clear activation narrative (Days 1–30 intake, 31–60 operationalize, 61–90 scale). Closest direct competitor to ActReady's control-mapping concept.
- **Heavy/clunky to beat:** Enterprise-focused (Global 2000 + mid-market), demo-gated, "live in 90 days" — slow relative to a PLG self-serve <5-min first-score goal. **ActReady's differentiator is artifact-native evidence (real eval JSON / model cards), not control *assertion*.** Trustible scores controls; ActReady *derives* them from artifacts.
- **Cite:** [trustible.ai](https://trustible.ai), [platform-overview](https://trustible.ai/platform-overview), [types-of-platforms](https://trustible.ai/post/types-of-ai-governance-platforms).

**Cross-competitor takeaway:** Every incumbent either (1) stops at infrastructure controls (Vanta), (2) is enterprise-dense/config-heavy (OneTrust, Holistic AI), or (3) asserts controls without ML-artifact grounding (Trustible, and fatally Delve). The PLG opening: **self-serve, ML-artifact-native, deterministic, <5-min first score, auditor-trustworthy by construction.**

---

## 3. DESIGN DIRECTION

**Recommended stack:** **Vite + React + TypeScript + Tailwind CSS + shadcn/ui**, with **Recharts** (or **TanStack Charts** / lightweight **visx**) for dashboards, **TanStack Query** for server state, **React Router** for routing, and **Zod** (already adjacent to the engine's pydantic contracts) for client validation.

**Reasoning:**
- **Team fit:** The team is React-strong; no context-switch cost. React + TS is the default for dev-tool PLG UIs.
- **Vite:** Fast dev server + build; ideal for a SPA talking to the existing FastAPI `POST /assess`. No SSR needed for an authenticated B2B dashboard (SEO is on the open catalogs/marketing site, not the app).
- **Tailwind + shadcn/ui:** shadcn/ui is a *source-distribution* component system (the CLI writes component TS into your repo) built on Radix primitives — accessible, themeable via CSS variables, fully owned/editable, and the de-facto choice for React teams using AI coding tools ([Vercel: what is shadcn/ui](https://vercel.com/i/what-is-shadcn); [shadcn/ui Vite install](https://ui.shadcn.com/docs/installation/vite)). This gives a polished, consistent, dev-tool aesthetic fast without a heavy design-ops burden — exactly the PLG feel that beats enterprise clunk.
- **Charts:** Recharts is declarative, React-native, and sufficient for scorecards/sparklines/bars. Avoid heavy BI libs (no Tableau-embed weight).
- **Server state:** TanStack Query handles the `POST /assess` polling, integration sync states, and report generation cleanly.
- **Shared contracts:** Define client types from the engine's `GapReport`/`Control`/`Obligation` pydantic models (or generate from the OpenAPI `POST /assess` spec) so frontend and API never drift.

**Design language:** Clean, light, high-information-density (GRC users *want* data), with a restrained accent color for status (green/amber/red semantic chips). Borrow Vanta's "one hero number + scannable panels" layout, but keep it lighter and faster than OneTrust's dense console. Mobile: read-only scorecard only; authoring is desktop.

**Hosting (UNVERIFIED):** Vercel/Netlify static SPA + FastAPI backend (separate deploy) is the natural fit; confirm in planning.

---

## 4. UX FLOWS

### Flow A — Activation (signup → first integration → first score in <5 min)
1. **Signup / email verify** → workspace created.
2. **Onboarding wizard:** "What are you preparing for?" (enterprise review / ISO 42001 / EU AI Act) → pre-selects framework scope.
3. **Connect first source** (fastest path: "Upload a model card YAML" or "Paste eval JSON" or "Connect GitHub repo"). One-click, no sales call.
4. **Auto-run assessment** on first ingest → redirect to **Readiness Scorecard** with the computed % and worst-first gaps.
5. **Aha moment copy:** "You're 41% ready for ISO 42001. Here are your 3 biggest gaps." CTA to close the top gap.
6. **Share prompt:** offer a watermarked markdown report (free tier) or secure link (paid).

*Target: signup → score < 5 minutes, zero human assistance. Mirrors Delve's "TurboTax-style" and Trustible's 30/60/90 narrative but self-serve.*

### Flow B — Recurring audit-ready (continuous)
1. User connects integrations (GitHub/MLflow) → evidence auto-syncs on a schedule.
2. Readiness Scorecard updates; freshness strip warns on 180-day expiries.
3. Weekly digest email: "2 controls went stale, 1 new gap from added obligation."
4. User opens Control Library → filters `missing` → follows remediation hint → uploads artifact → status flips `missing → satisfied` live.
5. Before a review/audit: open Audit/Export → generate report → share.

### Flow C — Share-with-auditor
1. From Audit/Export view → "Generate secure link" (read-only, scoped, expiring).
2. Auditor opens link → sees scorecard + evidence vault (scoped per Vanta's "you decide what auditors see" pattern) with **traceable artifacts** (each control → linked dated evidence, no auto-asserted conclusions — the Delve-lessons-learned guardrail).
3. Auditor can download PDF/markdown; comments/requests route back as evidence requests.
4. v0.4: dedicated auditor read-only view (in roadmap).

---

## 5. OPEN QUESTIONS (planning-phase scope decisions)

1. **Auth & multi-user:** Is v0.2 single-user/local or does it need auth (email/password, SSO) + workspaces? Affects every screen. *Recommend: lightweight email auth + single workspace for v0.2, multi-workspace deferred to v0.4 (matches roadmap).*
2. **Persistence layer:** Where do assessments, evidence metadata, and historical snapshots live? (Postgres? the engine is currently stateless/file-based.) Needed for diffable reports (v0.2) and the readiness-over-time sparkline.
3. **Evidence storage:** Store artifact bytes where — object storage (S3/R2) or just metadata + source links? Determines Vault UX and auditor-trust/provenance model.
4. **Integrations priority:** Which connectors first — GitHub model cards, MLflow, or promptfoo/deepeval? (Repo roadmap doesn't yet specify; see §1f UNVERIFIED.) *Recommend: GitHub + manual upload for v0.2; MLflow/promptfoo next.*
5. **Scoring display semantics:** Show the raw engine score, or a "frameworks-covered %" like Trustible's bars? Do we surface `partial` as 0.5 in the headline or separately? Affects Scorecard design.
6. **Report export fidelity:** PDF via what — client-side (react-pdf / print-CSS) or server-side (the FastAPI layer)? Markdown is trivial; PDF needs a decision.
7. **Free vs paid gating in UI:** Where does the watermarked-summary free tier end and paid (full export, secure links, integrations) begin? Needs a pricing-tier flag in the data model.
8. **REVIEW-COUNSEL surfacing:** How prominently do we show uncertain mappings? Inline-in-drawer (recommended) vs a separate "needs legal review" queue.

---

## 6. FRONTEND MVP SCOPE (v0.2 recommendation)

Prioritized screens for the first web UI, ordered by value-to-effort against the activation flow:

**P0 — must ship for a usable v0.2:**
1. **Auth + workspace shell** (login, nav, layout) — foundational.
2. **Readiness Scorecard / Overview** (1a) — the hero screen; proves value instantly.
3. **Control Library View** (1b) — filter by satisfied/partial/missing; the daily-driver.
4. **Per-Control Detail Drawer** (1d) — obligation mapping, remediation hint, freshness.
5. **Manual Upload → Evidence Vault (minimal)** (1c) — upload model card / eval JSON / incidents; show ingest status + linked control. (GitHub connector nice-to-have, not blocking.)
6. **Audit/Export View — Markdown + JSON** (1e) — generate & download the gap report; PDF deferred.

**P1 — fast follow (end of v0.2 / v0.3):**
7. **Integrations Page** (1f) — GitHub connector + MLflow; auto-sync states.
8. **Readiness-over-time sparkline** (needs persistence/history).
9. **Share-with-auditor secure link** (1c flow C) — read-only scoped view.

**P2 — later (v0.3+):**
10. **Policy/Playbook Generator** (1g).
11. **Audit comments/requests loop**, multi-workspace, auditor dedicated view (v0.4).

**Rationale:** P0 delivers the full "connect artifacts → see score → understand gaps → export report" loop in <5 min, directly enabling the PLG GTM wedge (research brief §4) and the kill-criteria metric ("partner passes a buyer's review using ActReady output"). It reuses the existing engine output with minimal new backend beyond auth + persistence.

---

### Sources
- ActReady repo: `README.md`, `docs/research-brief.md`, `docs/tam-sam-som.md` (local, accessed 2026-08-29).
- Vanta: [automated-compliance](https://www.vanta.com/products/automated-compliance), [audit](https://www.vanta.com/products/audit), [features](https://www.vanta.com/features), [Evidence Collection help center](https://help.vanta.com/en/collections/12734665-evidence-collection).
- Delve: [delve.co/learn](https://delve.co/learn/grc/ai-transforming-grc-compliance); Systima investigation [systima.ai/blog](https://systima.ai/blog/delve-compliance-fraud-eu-ai-act-conformity-assessment); LinkedIn post (acknowledging discontinued automation).
- OneTrust: [ai-governance](https://www.onetrust.com/solutions/ai-governance/), [platform](https://www.onetrust.com/platform/), [enterprise-scale](https://www.onetrust.com/why-onetrust/ai-governance-at-enterprise-scale/).
- Holistic AI: [holisticai.com](https://www.holisticai.com), [ai-governance-platform](https://www.holisticai.com/ai-governance-platform).
- Trustible: [trustible.ai](https://trustible.ai), [platform-overview](https://trustible.ai/platform-overview), [types-of-platforms](https://trustible.ai/post/types-of-ai-governance-platforms).
- Design system: [shadcn/ui Vite install](https://ui.shadcn.com/docs/installation/vite), [Vercel: what is shadcn/ui](https://vercel.com/i/what-is-shadcn).

*Assumptions marked UNVERIFIED inline: historical snapshot storage, integration connector list, policy-generator existence, and hosting model.*
