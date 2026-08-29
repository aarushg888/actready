# ActReady

**ActReady is an AI-governance evidence compiler.** Teams shipping AI products face a growing
pile of obligations — ISO/IEC 42001 controls, EU AI Act Articles 9–15 — but the evidence that
proves compliance is scattered across model cards, eval exports, incident trackers and policy
docs. Auditors and enterprise buyers ask "show me," and the answer today is a frantic
spreadsheet archaeology session. ActReady ingests the artifacts you already produce
(model card YAML, promptfoo/deepeval eval JSON, incidents CSV), deterministically maps them
against a versioned catalog of controls and obligations, and outputs a scored gap report —
markdown for humans, JSON for machines.

> ⚠️ **Disclaimer:** ActReady v0.1 is an engineering aid, not legal advice, not a
> certification body, and not a conformity assessment. Control/obligation mappings are
> condensed heuristics seeded by hand (flagged `REVIEW-COUNSEL` where uncertain). Have counsel
> review anything you rely on for regulatory purposes.

## Quickstart

Requires Python >= 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/aarushg888/actready.git
cd actready/api
uv sync                                        # install deps into .venv

uv run uvicorn app.main:app --port 8000        # start the API
# in another shell:
curl -s http://localhost:8000/healthz          # {"status":"ok","version":"0.1.0"}

curl -s -X POST http://localhost:8000/assess \
  -F "files=@../api/tests/fixtures/model_card.yaml" \
  -F "files=@../api/tests/fixtures/promptfoo_run.json" \
  -F "files=@../api/tests/fixtures/incidents.csv"
```

Or run the engine directly:

```bash
cd api
uv run python - <<'PY'
from app.ingest import collect_evidence
from app.mapper import map_evidence
from app.report import render_markdown

evidence = collect_evidence(
    model_card_yaml=open("tests/fixtures/model_card.yaml").read(),
    eval_run_json=open("tests/fixtures/promptfoo_run.json").read(),
    incidents_csv=open("tests/fixtures/incidents.csv").read(),
)
print(render_markdown(map_evidence(evidence)))
PY
```

Optional LLM explanations (off by default; the engine never needs them):

```bash
ACTREADY_PROVIDER=fake   uv run python -c "..."   # offline canned provider
ACTREADY_PROVIDER=openai uv run python -c "..."   # instructor + OpenAI (needs OPENAI_API_KEY)
```

## Architecture

```
evidence in                deterministic engine                 out
──────────────             ────────────────────                 ──
model_card.yaml ─┐    ┌──────────────┐   ┌───────────────┐
eval_run.json  ──┼──▶▶│ app.ingest    │▶▶│ app.mapper     │      markdown report
incidents.csv  ──┘    │  normalize    │   │  score each    │──▶  (app.report) or
                      └──────────────┘   │  control:      │     GapReport JSON
data/controls_iso42001.yaml ─┐           │  satisfied /   │     (FastAPI POST /assess)
data/obligations_eu_ai_act ──┘           │  partial /     │
                                         │  missing       │
                                         └───────┬────────┘
                                                 ▼ obligation rollup
                                   optional LLM prose (app.explain,
                                   ACTREADY_PROVIDER, default none)
```

- **`app/models.py`** — pydantic contracts: `Evidence`, `Control`, `Obligation`, `GapItem`, `GapReport`.
- **`app/catalog.py`** — strict loaders for versioned YAML catalogs under `data/`.
- **`app/ingest.py`** — parsers with field-path errors (`IngestError`).
- **`app/mapper.py`** — deterministic scoring: *satisfied* iff matching-type evidence exists
  and was collected within **180 days**; *partial* if only stale evidence; *missing* otherwise.
  Obligations roll up from control links; readiness score = `(satisfied + 0.5·partial) / total`.
- **`app/report.py`** — markdown renderer (scorecard table, worst-first gaps, standards citations).
- **`app/main.py`** — FastAPI: `POST /assess` (multipart files[]), `GET /healthz`.
- **`app/explain.py`** — optional LLM explanations via instructor; lazy imports so tests make zero network calls.

## Roadmap

- [x] v0.1 — deterministic engine, seeded catalogs (ISO 42001 Annex A condensed; EU AI Act Art. 9–15), FastAPI, gap reports
- [ ] v0.2 — SOC 2 / NIST AI RMF catalogs; per-obligation deep-link rendering; diffable reports over time
- [ ] v0.3 — CI integration (fail PRs that introduce new gaps); evidence freshness policies per control class
- [ ] v0.4 — multi-workspace API, auditor read-only views, export to Vanta/Drata-style evidence packets

## Development

```bash
cd api
uv run pytest --cov=app -q     # tests + coverage (gate >=80%)
uv run ruff check .            # lint
uv run mypy .                  # types
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions and the PR checklist.

## Research & v0.2 planning

This repo is research-driven. The gold idea (ActReady) was selected after a full
market/competitor/feasibility gauntlet; the v0.2 scope below is the output of a
multi-agent ideation → planning loop.

- **Market & competitive research:** [docs/research-deep-dive.md](docs/research-deep-dive.md) — EU AI Act + ISO 42001 obligations, 12-competitor landscape, the confirmed gap (no incumbent compiles evidence from ML pipelines), demand signals.
- **Domain research briefs:** [backend](docs/backend-research.md) · [frontend](docs/frontend-research.md) · [ML/AI](docs/ml-research.md)
- **v0.2 plans (decision-locked):** [backend](docs/planning/backend-plan.md) · [frontend](docs/planning/frontend-plan.md) · [ML](docs/planning/ml-plan.md) · [product strategy & milestones](docs/planning/product-plan.md)
- **Consolidated backlog + top-10:** [ISSUES.md](ISSUES.md)
- **Target architecture sketch:** [ARCHITECTURE.md](ARCHITECTURE.md)
- Earlier v0.1 market sizing: [docs/tam-sam-som.md](docs/tam-sam-som.md), [docs/research-brief.md](docs/research-brief.md)

## License

[MIT](LICENSE) © 2026 Aarush Gutha
