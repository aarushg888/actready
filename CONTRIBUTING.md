# Contributing to ActReady

Thanks for your interest in improving ActReady — an AI-governance evidence compiler
that maps real evidence (model cards, eval runs, incident logs) against
ISO/IEC 42001 controls and EU AI Act (Regulation (EU) 2024/1689) Articles 9–15 obligations.

## Setup

ActReady uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

```bash
git clone https://github.com/aarushg888/actready.git
cd actready/api
uv python install 3.11   # or any >=3.11 interpreter
uv sync                  # creates .venv and installs deps + dev group
```

## Local development loop

```bash
cd api
uv run pytest --cov=app -q      # tests + coverage (gate: >= 80%)
uv run ruff check .             # lint (gate: zero findings)
uv run mypy .                   # type check (gate: clean)
uv run uvicorn app.main:app --reload   # run the API locally at :8000
```

## Branch naming

- `feat/<short-slug>` — new capability (e.g. `feat/csv-bulk-import`)
- `fix/<short-slug>` — bug fix (e.g. `fix/stale-evidence-boundary`)
- `chore/<short-slug>` — tooling, deps, docs-only changes

## PR checklist

Before opening a pull request, confirm:

- [ ] Tests pass locally (`uv run pytest -q` from `api/`)
- [ ] Coverage stays **>= 80%** (`uv run pytest --cov=app --cov-fail-under=80 -q`)
- [ ] `uv run ruff check .` is clean
- [ ] `uv run mypy .` is clean
- [ ] New catalog entries (`data/*.yaml`) include `evidence_types`, and for EU AI Act
      obligations an `eur-lex.europa.eu` `source_url`
- [ ] Any control→obligation mapping you are unsure about carries a
      `REVIEW-COUNSEL: true` note in the YAML comment/description
- [ ] No secrets, tokens, or customer data in fixtures

## Design rules

1. **The engine is deterministic.** LLM calls live only behind `ACTREADY_PROVIDER`
   (default `none`) and must never be required to produce a gap report.
2. **Catalogs are data.** Controls and obligations live in versioned YAML under `data/`,
   not code.
3. **Tests make no network calls.** Ever.

## License

MIT — see [LICENSE](LICENSE).
