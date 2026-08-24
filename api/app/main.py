"""FastAPI surface: POST /assess (multipart files[]) and GET /healthz."""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.ingest import IngestError, collect_evidence
from app.mapper import map_evidence
from app.models import GapReport
from app.report import render_markdown

app = FastAPI(
    title="ActReady",
    version="0.1.0",
    description="AI-governance evidence compiler: ISO/IEC 42001 + EU AI Act gap reports.",
)

_SUFFIX_KIND = {
    ".yaml": "model_card_yaml",
    ".yml": "model_card_yaml",
    ".json": "eval_run_json",
    ".csv": "incidents_csv",
}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/assess", response_model=GapReport)
async def assess(files: Annotated[list[UploadFile], File(min_length=1)]) -> GapReport:
    """Ingest uploaded evidence files and return a scored GapReport."""
    model_card_yaml: str | None = None
    eval_run_json: str | None = None
    incidents_csv: str | None = None

    for upload in files:
        suffix = "." + (upload.filename or "").rsplit(".", 1)[-1].lower()
        kind = _SUFFIX_KIND.get(suffix)
        if kind is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"unsupported file type for {upload.filename!r}; "
                    f"expected .yaml/.yml (model card), .json (eval run) or .csv (incidents)"
                ),
            )
        raw = await upload.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"{upload.filename}: not UTF-8 text ({exc})") from exc

        if kind == "model_card_yaml":
            if model_card_yaml is not None:
                raise HTTPException(status_code=422, detail="multiple model cards uploaded; expected at most one")
            model_card_yaml = text
        elif kind == "eval_run_json":
            eval_run_json = text  # last one wins; multiple runs are appended content-wise
        else:
            incidents_csv = text if incidents_csv is None else f"{incidents_csv}{text}"

    try:
        evidence = collect_evidence(
            model_card_yaml=model_card_yaml,
            eval_run_json=eval_run_json,
            incidents_csv=incidents_csv,
        )
    except IngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return map_evidence(evidence)


@app.get("/assess/markdown", response_model=None)
async def assess_markdown_hint() -> dict[str, str]:
    """Human-friendly hint: markdown rendering is available in the CLI/report module."""
    return {
        "hint": "POST /assess with multipart files[], then render via app.report.render_markdown",
        "example": render_markdown.__doc__ or "",
    }
