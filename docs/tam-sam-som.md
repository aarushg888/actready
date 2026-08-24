# ActReady — Market Sizing (TAM / SAM / SOM)

**Method:** bottom-up. Every input carries a value, source URL, confidence (H/M/L), and date accessed.
**Date accessed for all inputs: 2026-08-23.** Items we could not verify against a primary source are marked **UNVERIFIED**.

---

## TAM — annual governance-evidence tooling spend by orgs shipping AI products in scope of EU AI Act / ISO 42001

**Formula:**

```
TAM = (# companies shipping AI products subject to EU AI Act or seeking ISO 42001)
    × (annual governance/compliance tooling budget per company, $15K–$50K)
```

### Input 1 — number of companies shipping AI products

| Input | Value | Source | Confidence | Accessed |
|---|---|---|---|---|
| Organizations using AI in ≥1 business function | 78% (2024 survey); 88% (2025 survey) | [McKinsey State of AI coverage](https://explodingtopics.com/blog/companies-using-ai) and [survey summary](https://www.lootzysoft.com/blog/the-state-of-ai-in-2025-closing-the-gap-between-adoption-and-impact) | H | 2026-08-23 |
| Share building vs. buying AI capabilities | 47% develop internally, 53% buy from vendors | [McKinsey State of AI summary](https://www.punku.ai/blog/state-of-ai-2024-enterprise-adoption) | M | 2026-08-23 |
| EU AI Act scope: provider obligations apply extraterritorially (output used in the EU counts) | qualitative | [EU AI Act high-level summary](https://artificialintelligenceact.eu/high-level-summary/) | H | 2026-08-23 |
| Companies worldwide estimated inside *some* AI Act obligation band (provider/deployer of AI systems touching the EU market) | **~60,000** (range 40,000–80,000) | Derived: no single census exists. Anchors: 78–88% adoption applied to ~6–8M employer firms in the US alone implies millions of *AI users*; narrowing to firms that *ship an AI system/product* (build or materially integrate models under their name) yields low tens of thousands across US+EU+UK. Cross-checked against Vanta's 12,000 compliance customers as a proxy for the compliance-buying subset ([Sacra](https://sacra.com/c/vanta/)). **UNVERIFIED — treat the count as an assumption band, not a measurement.** | L | 2026-08-23 |

### Input 2 — governance tooling budget per company

| Input | Value | Source | Confidence | Accessed |
|---|---|---|---|---|
| Compliance automation platform pricing (mid-market tiers) | roughly $10K–$80K/yr depending on tier (e.g. Vanta tiers described at ~$45K–$80K for advanced plans; entry plans lower) | [Topickz Vanta profile](https://topickz.com/software/vanta-com?review=1) | M | 2026-08-23 |
| Assumed ActReady-relevant budget slice (evidence compilation & gap analysis for AI frameworks) | **$15K–$50K/yr**, midpoint **$25K** | Conservative slice of total GRC budget; consistent with pricing above. **Assumption.** | L | 2026-08-23 |

### Computation

```
TAM (point)   = 60,000 orgs × $25K          = $1.5B / yr
TAM (low)     = 40,000 orgs × $15K          = $0.6B / yr
TAM (high)    = 80,000 orgs × $50K          = $4.0B / yr
```

**TAM ≈ $1.5B annually ($0.6B–$4.0B range).** Sanity check: Sacra sizes total compliance/spend-adjacent markets at $140B+, so even our high case is <3% of the broader category ([Sacra](https://sacra.com/c/vanta/), M, 2026-08-23).

---

## SAM — AI-native startups, 10–500 employees, US + EU, B2B, shipping AI products

**Formula:**

```
SAM = (# AI-native B2B startups 10–500 FTE in US+EU) × ACV ($12K)
```

| Input | Value | Source | Confidence | Accessed |
|---|---|---|---|---|
| AI-native startups US+EU (founded ≥2020, AI is the product) | **~25,000** (US ~15K, EU ~10K) | Deal-tracking aggregates put active AI startups far higher globally; filtering to B2B, 10–500 FTE, still operating in 2026 gives this band. **UNVERIFIED — derived estimate.** | L | 2026-08-23 |
| Enterprise-deal-driven need for evidence artifacts (security reviews, AI governance questionnaires) | qualitative: Delve grew 100→500+ customers in months selling exactly this motion to AI startups | [TechCrunch on Delve](https://techcrunch.com/2025/07/22/21-year-old-mit-dropouts-raise-32m-at-300m-valuation-led-by-insight/) | M | 2026-08-23 |
| ACV for a deterministic evidence/gap-reporting tier | **$12K/yr** | Priced below Vanta/Delve platform deals to reflect a single-framework wedge. **Assumption.** | L | 2026-08-23 |

```
SAM = 25,000 × $12K = $300M / yr
```

---

## SOM — year 1

**Formula:**

```
SOM(year 1) = (# paid pilot→paid conversions in first 12 months) × ACV
            = 30–60 orgs × $12K
```

| Input | Value | Source | Confidence | Accessed |
|---|---|---|---|---|
| Year-1 paid org target (PLG free tier + design partners + founder-led sales) | **30–60 orgs** | Internal plan; benchmarked against Delve's early trajectory (100→500 customers in ~6 months post-seed, though better-funded: [TechCrunch](https://techcrunch.com/2025/07/22/21-year-old-mit-dropouts-raise-32m-at-300m-valuation-led-by-insight/)) | L | 2026-08-23 |
| ACV | $12K | As above | L | 2026-08-23 |

```
SOM(year 1) = $360K – $720K ARR
```

This is deliberately modest: year 1 buys proof (retention, auditor acceptance, catalog depth), not scale.

---

## Confidence summary

The weakest link in the chain is the absolute count of in-scope companies — no regulator publishes a register yet. The strongest signals are directional: near-universal AI adoption (McKinsey, H), binding EU AI Act dates (Aug 2026 high-risk obligations, H), and two well-funded comps validating willingness-to-pay in adjacent compliance categories (Vanta, Delve, H on funding facts). Re-run this model quarterly as AI Act conformity data emerges.
