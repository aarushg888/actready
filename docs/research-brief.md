# ActReady Research Brief

**Date:** 2026-08-23 · **Author:** Aarush Gutha · **Status:** v0.1 working thesis

---

## 1. Problem

Every company shipping an AI product is accumulating legal and contractual obligations —
EU AI Act Articles 9–15 for anything touching the EU market, ISO/IEC 42001 for anyone facing
an enterprise procurement process — but the *evidence* that proves compliance lives in
fragments: a model card in one repo, eval exports in another, incident post-mortems in a
tracker, policies in a doc drive. When an auditor, enterprise buyer, or regulator asks
"show me," teams reconstruct the story by hand, weeks at a time.

The people closest to the pain describe it consistently:

> "The eval scores are green, and an hour ago the model still handed a confidently wrong
> answer to a real user."
>
> — practitioner thread on evaluation-vs-reality gaps,
> [reddit.com/r/LangChain/comments/1uvc827](https://www.reddit.com/r/LangChain/comments/1uvc827/)

Green dashboards are not evidence. Eval runs capture a snapshot; obligations demand
continuous, dated, attributable proof. The gap between "we test our models" and "here is the
artifact trail for Article 11(1)" is exactly where deals stall and audit findings land.

> Teams describe hitting a ceiling with spreadsheet-based LLM QA: rows of manual test cases,
> screenshots pasted into sheets, no lineage from requirement to result.
>
> — practitioner thread on spreadsheet-based QA limits,
> [reddit.com/r/softwaretesting/comments/1vky2t1](https://www.reddit.com/r/softwaretesting/comments/1vky2t1/)

Spreadsheets scale to a handful of models and collapse at ten. There is no versioned catalog
of what evidence must exist, no freshness tracking, and no rollup from technical artifacts to
the legal articles an enterprise buyer actually cites.

> After silent hallucinations reached production, practitioners report hand-verifying outputs
> and assembling documentation after the fact — retrofitted governance rather than designed
> evidence trails.
>
> — practitioner thread on silent hallucinations and manual verification burden,
> [reddit.com/r/mlops/comments/1v0i3cd](https://www.reddit.com/r/mlops/comments/1v0i3cd/)

Retroactive evidence gathering is the most expensive possible mode of compliance: it happens
under deadline pressure, mid-deal, with incomplete records. ActReady's bet is that evidence
compilation should be a deterministic byproduct of shipping, not a fire drill.

**Why now:** The EU AI Act's high-risk obligations (Articles 9–17) bind from
**2 August 2026** for Annex III systems (with Annex I embedded systems following in 2027);
Article 11 requires the Annex IV technical documentation package to exist *before* market
placement and be kept current for ten years ([artificialintelligenceact.eu timeline](https://artificialintelligenceact.eu/implementation-timeline/),
[CSA analysis](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-compliance-deadline-20/),
accessed 2026-08-23). Even amid proposals to delay certain deadlines, enterprises are being
counseled to treat August 2026 as operative ([CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-compliance-deadline-20/)).
Meanwhile ISO/IEC 42001 certification requests are appearing in enterprise AI procurement as
the de-facto "prove you manage AI" artifact. First-wave adopters need evidence tooling now;
the majority arrive through 2027.

---

## 2. Ideal Customer Profile

**Firmographics**

- B2B AI-native companies, 10–500 employees, US + EU
- Shipping an AI system as the product (agents, copilots, vertical AI, model-powered SaaS)
- Selling upmarket: security review / procurement questionnaires arriving in the sales cycle
- Some subset already asked for ISO 42001 or EU AI Act artifacts by a customer or auditor

**Persona: the Head of AI Platform / Founding ML Engineer who got handed compliance**

- Owns both the pipeline and now the paperwork; reports to a CTO selling into enterprise
- Already runs promptfoo/deepeval; already writes internal model cards
- Pain peaks quarterly: enterprise security reviews, renewal audits, board questions
- Buys tools that work in CI and produce artifacts a human auditor accepts

**Buying triggers**

1. An enterprise deal stalls on an AI-governance questionnaire (most common)
2. A customer contractually requires ISO 42001 alignment or EU AI Act Art. 13 instructions-for-use docs
3. First real incident triggers a post-mortem demanding evidence the team doesn't have organized
4. An auditor names a date ("conformity assessment in Q3")

**Objections, honestly answered**

- *"We'll do this manually."* Fine until the second framework or the tenth model; the cost curve is super-linear.
- *"Isn't this Vanta?"* Vanta automates infrastructure controls (SOC 2). It does not parse your eval exports or model cards into Article 11 documentation.
- *"We're pre-regulation."* Your buyers aren't. Evidence requests precede enforcement dates by quarters.
- *"Another dashboard?"* ActReady produces no dashboard to live in; it compiles artifacts you must produce anyway.

---

## 3. Competition

**Compliance automation platforms (adjacent, expanding)**

- **Vanta** — trust management leader; ~12,000 customers; raised $150M at a $4.15B valuation
  (July 2025), total funding ≈ $500M; explicitly expanding frameworks and shipping AI risk
  features ([Forbes](https://forbes.com/sites/phoebeliu/2025/07/23/christina-cacioppos-startup-vanta-raised-new-funds-at-a-4-billion-valuation-despite-not-needing-the-money),
  [Sacra](https://sacra.com/c/vanta/), accessed 2026-08-23).
- **Delve** — AI-agent compliance automation, HIPAA-first then "alphabet soup"; $32M Series A
  led by Insight Partners at $300M valuation (July 2025); grew 100→500+ customers in months
  ([TechCrunch](https://techcrunch.com/2025/07/22/21-year-old-mit-dropouts-raise-32m-at-300m-valuation-led-by-insight/),
  [Delve announcement](https://delve.co/blog/series-a), accessed 2026-08-23).
- **Drata, Anecdotes** — same category: continuous control monitoring across cloud/BizOps
  integrations, broad framework libraries, strong auditor networks. None natively ingest
  ML-specific artifacts (eval JSON, model card YAML) or map them to Articles 9–15.

These platforms answer *"are your laptops encrypted and your policies signed?"* ActReady
answers *"where is the dated evidence that your model's data governance satisfies Article 10?"*
Different evidence plane. Expect them to become acquirers/partners more than killers before 2028.

**Eval platforms (tooling adjacency, not competition)**

- **Promptfoo** — acquired by OpenAI (March 2026); used by >25% of Fortune 500 for evals/red-teaming;
  its future is inside OpenAI Frontier ([OpenAI](https://openai.com/index/openai-to-acquire-promptfoo/),
  [TechCrunch](https://techcrunch.com/2026/03/09/openai-acquires-promptfoo-to-secure-its-ai-agents/), accessed 2026-08-23).
- **Braintrust, LangSmith** — hosted eval/observability suites owned by platform vendors.

**Why ActReady is NOT an eval dashboard:** Evals measure model behavior at a point in time.
ActReady consumes those results as *evidence* and answers a different question — not
"is this model good?" but "can you prove, with fresh dated artifacts, that each applicable
control and obligation is covered?" We sit downstream of every eval tool, normalize their
exports, and stay useful even when a team changes eval vendors. Deterministic mapping is the
product; LLM prose is optional garnish behind `ACTREADY_PROVIDER` (default off).

---

## 4. Go-To-Market — first 90 days

1. **Days 0–30 · PLG wedge:** Free tier = run the compiler locally/CI against your own
   fixtures; output is a shareable markdown gap report (watermarked summary). Publish the
   catalogs openly (versioned YAML) — they double as SEO surface and community contribution
   point ("submit a control mapping").
2. **Days 15–60 · Design partners:** Recruit 5–10 AI-native startups mid-security-review.
   Weekly cadence; success metric = a partner passes a buyer's AI-governance review using
   ActReady output. Case study rights negotiated upfront.
3. **Days 45–90 · Auditor partnerships:** Two partnerships with boutique audit firms doing
   ISO 42001 readiness; they receive structured evidence packets, refer clients. Auditors
   are the distribution channel incumbents ignore.

Pricing gate: paid pilot tier lands around **$12K ACV** (see [tam-sam-som.md](tam-sam-som.md)).

**Kill criteria (pre-committed):**

- Fewer than **3 paid pilots** within 90 days of first design-partner launch → stop, write up findings.
- <40% of free-tier users return within 14 days → distribution problem, fix wedge before spending on partners.
- Any partner fails a real audit using ActReady output → halt GTM, fix engine credibility first.

## 5. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| EU AI Act deadlines slip (Nov 2025 delay proposal not yet law) | High | Sell to buying triggers that exist today (enterprise questionnaires, ISO 42001 asks), not the statute date |
| Incumbents (Vanta/Delve) add AI-artifact ingestion | High | Depth moat: catalog quality + auditor acceptance; stay acquisition-friendly |
| Mapping liability — wrong control↔article advice | Medium | `REVIEW-COUNSEL` flags, citations to EUR-Lex text, explicit not-legal-advice posture, counsel advisory circle |
| Standards churn (ISO amendments, harmonized standards) | Medium | Catalogs are versioned data, not code; re-certification is a diff, not a rewrite |
| Eval-tool consolidation shrinks upstream sources | Low-Medium | Normalizer layer is pluggable; raw JSON/CSV/YAML always supported |
| Open-source catalogs copied without attribution | Low | MIT anyway — moat is freshness + auditor network, not the YAML |

## 6. Sources

Practitioner threads: [r/LangChain](https://www.reddit.com/r/LangChain/comments/1uvc827/) ·
[r/softwaretesting](https://www.reddit.com/r/softwaretesting/comments/1vky2t1/) ·
[r/mlops](https://www.reddit.com/r/mlops/comments/1v0i3cd/)
(accessed 2026-08-23).

Regulatory: [EUR-Lex Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) ·
[AI Act implementation timeline](https://artificialintelligenceact.eu/implementation-timeline/) ·
[CSA deadline note](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-compliance-deadline-20/).

Market & competitors: [Vanta (Wikipedia)](https://en.wikipedia.org/wiki/Vanta_(company)) ·
[Vanta @ $4.15B (Forbes)](https://forbes.com/sites/phoebeliu/2025/07/23/christina-cacioppos-startup-vanta-raised-new-funds-at-a-4-billion-valuation-despite-not-needing-the-money) ·
[Sacra on Vanta](https://sacra.com/c/vanta/) ·
[Delve Series A (TechCrunch)](https://techcrunch.com/2025/07/22/21-year-old-mit-dropouts-raise-32m-at-300m-valuation-led-by-insight/) ·
[OpenAI–Promptfoo](https://openai.com/index/openai-to-acquire-promptfoo/) ·
[McKinsey State of AI coverage](https://www.lootzysoft.com/blog/the-state-of-ai-in-2025-closing-the-gap-between-adoption-and-impact/).

All URLs accessed 2026-08-23.
