"""Reporting routers: report export + public share link.


Endpoints:
  * ``GET /api/report?format=json|markdown|html|pdf`` — render the latest
    snapshot (or a supplied report) for the authenticated tenant. ``pdf`` is
    optional: when WeasyPrint is unavailable it returns 501 + the HTML fallback.
  * ``GET /api/share/{token}`` — public, credential-free read of a snapshot via a
    signed share link.

WIRING (M3 owns this; M1 owns app.main.py):
  The routers are NOT auto-included because M1 may own ``main.py``. To enable,
  add the following to ``app/main.py`` (commented until M1 confirms ownership):

      # from app.reporting.router import report_router, share_router
      # app.include_router(report_router)
      # app.include_router(share_router)

  This file is import-safe on its own and is exercised directly by the test
  suite (see tests/test_reporting.py).
"""
# ruff: noqa: B008  # FastAPI Depends() in arg defaults is the documented pattern

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.models import GapReport
from app.models_db import ReportSnapshot
from app.reporting import export
from app.reporting.share import ShareInvalid, ShareRevoked, verify_share

report_router = APIRouter(prefix="/api/report", tags=["report"])
share_router = APIRouter(prefix="/api/share", tags=["share"])

# --- DB session seam (M3-local; M1 will replace get_db with tenant-scoped) ---
# M3 does not own the DB session seam (M1 does). Call ``set_engine`` with a real
# SQLAlchemy engine so the share endpoint can read snapshots + revocation state.
_ENGINE: Any | None = None


def set_engine(engine: Any) -> None:
    """Register a SQLAlchemy engine so routers can open a DB session."""
    global _ENGINE
    _ENGINE = engine


def get_db() -> Iterator[Session]:
    """Yield a DB session, or raise 503 if no engine is configured yet."""
    if _ENGINE is None:
        raise HTTPException(status_code=503, detail="database not configured")
    with Session(_ENGINE) as s:
        yield s


# --- In-process report source for the report endpoint ----------------------
# M3 does not own the service layer (M1 does). For standalone operation we keep
# a module-level "latest report" holder; M1 will swap this for a tenant-scoped
# dependency that loads the report from the request principal.
_LATEST_REPORT: GapReport | None = None


def set_latest_report(report: GapReport) -> None:
    """Register the most-recently generated report for the router to render."""
    global _LATEST_REPORT
    _LATEST_REPORT = report


@report_router.get("")
@report_router.get("/")
def get_report(format: str = Query("json", pattern="^(json|markdown|html|pdf)$")) -> Response:
    report = _LATEST_REPORT
    if report is None:
        raise HTTPException(status_code=404, detail="no report generated yet")

    if format == "json":
        return JSONResponse(content=export.render_json(report))
    if format == "markdown":
        return PlainTextResponse(export.render_markdown(report), media_type="text/markdown")
    html_doc = export.render_html(report)
    if format == "html":
        return HTMLResponse(html_doc)
    # pdf (optional)
    if format == "pdf":
        try:
            pdf_bytes = export.render_pdf(html_doc)
        except export.WeasyUnavailable as exc:
            # Clear, documented fallback: 501 + the HTML so the caller still gets the report.
            return HTMLResponse(
                content=html_doc,
                status_code=501,
                headers={"X-PDF-Unavailable": "1", "X-PDF-Reason": str(exc)},
            )
        return Response(content=pdf_bytes, media_type="application/pdf")
    # Exhaustiveness guard: `pattern` constrains format to the four branches above.
    return Response(status_code=400, content=b"unsupported format")


@share_router.get("/{token}")
def public_share(token: str, db: Session = Depends(get_db)) -> Response:
    """Public read of a snapshot referenced by a signed share link (no tenant creds)."""
    try:
        payload = verify_share(token, db=db)
    except ShareRevoked:
        raise HTTPException(status_code=410, detail="share link revoked") from None
    except ShareInvalid as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None

    snapshot_id = payload.get("snapshot_id")
    if snapshot_id is None:
        raise HTTPException(status_code=404, detail="share link has no linked snapshot")

    row = db.get(ReportSnapshot, snapshot_id if isinstance(snapshot_id, uuid.UUID) else uuid.UUID(str(snapshot_id)))
    if row is None:
        raise HTTPException(status_code=404, detail="snapshot not found")

    data = row.report_json
    report = GapReport(
        items=data["items"],
        summary=data["summary"],
        generated_at=dt.date.fromisoformat(data["generated_at"]),
    )
    return HTMLResponse(export.render_html(report))


__all__ = ["report_router", "share_router", "set_latest_report", "set_engine", "get_db"]
