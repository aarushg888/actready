"""Report export renderers: Markdown, JSON, HTML, and (optional) PDF.


All renderers accept a ``GapReport`` (from ``app.models``) plus an optional
evidence list (each item must expose a ``source_name``/``type``/``collected_at``
or be a plain mapping). The HTML renderer is auditor-facing: it shows the
readiness score, a per-control status table, and evidence links.
"""
# ruff: noqa: E501  # long lines are intentional HTML/CSS template content

from __future__ import annotations

import html
import json
from collections.abc import Callable, Iterable
from typing import Any

from app.models import GapReport

# Reuse the v0.1 markdown renderer unchanged. Typed as Optional so the
# call-site is checked; mypy's no-redef is satisfied by assigning a typed
# variable rather than re-annotating the imported name.
_render_markdown_v1: Callable[[GapReport], str] | None
try:  # reuse the v0.1 markdown renderer unchanged
    from app.report import render_markdown as _render_markdown_v1
except Exception:  # pragma: no cover - app.report always present in-tree
    _render_markdown_v1 = None

# WeasyPrint has heavy native deps (cairo/pango/glib). Import is best-effort so
# the rest of reporting works on machines without those system libraries. When
# weasyprint is missing, render_pdf() raises WeasyUnavailable and the router
# returns a clear 501 ("pdf unavailable") — the HTML is still served as fallback.
try:  # pragma: no cover - exercised only when the lib is present
    import weasyprint

    _WEASYPRINT_AVAILABLE = True
except Exception:  # broad: ImportError, OSError (missing .dylib), etc.
    weasyprint = None
    _WEASYPRINT_AVAILABLE = False


STATUS_ORDER = {"missing": 0, "partial": 1, "satisfied": 2}
STATUS_LABEL = {"satisfied": "Satisfied", "partial": "Partial", "missing": "Missing"}
ISO42001_CITATION = "ISO/IEC 42001:2023, Information technology — Artificial intelligence — Management system"
EURLEX_BASE_URL = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"


class WeasyUnavailable(RuntimeError):
    """Raised when PDF rendering is requested but WeasyPrint cannot run."""


def weasyprint_available() -> bool:
    """True only when weasyprint imported AND its native libs actually load."""
    if not _WEASYPRINT_AVAILABLE:
        return False
    try:  # pragma: no cover - only reachable when lib is installed
        weasyprint.HTML(string="<p>x</p>").write_pdf()
        return True
    except Exception:
        return False


def render_markdown(report: GapReport) -> str:
    """Render the gap report as Markdown (delegates to v0.1 renderer)."""
    assert _render_markdown_v1 is not None, "v0.1 markdown renderer unavailable"
    return _render_markdown_v1(report)


def render_json(report: GapReport, evidence: Iterable[Any] | None = None) -> str:
    """Render the gap report as a pretty-printed JSON string."""
    payload: dict[str, Any] = {
        "summary": report.summary,
        "items": [item.model_dump(mode="json") for item in report.items],
        "generated_at": report.generated_at.isoformat(),
    }
    if evidence is not None:
        normalized: list[dict[str, Any]] = []
        for ev in evidence:
            if isinstance(ev, dict):
                normalized.append(ev)
            elif hasattr(ev, "model_dump"):
                normalized.append(ev.model_dump(mode="json"))
            elif hasattr(ev, "__dict__"):
                normalized.append(dict(ev.__dict__))
            else:  # pragma: no cover - defensive
                normalized.append({"value": str(ev)})
        payload["evidence"] = normalized
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _evidence_links(report: GapReport, evidence: Iterable[Any] | None) -> list[dict[str, str]]:
    """Build a small evidence manifest for the HTML/PDF 'Evidence' section."""
    if evidence is None:
        return []
    links: list[dict[str, str]] = []
    for i, ev in enumerate(evidence, start=1):
        if isinstance(ev, dict):
            etype = str(ev.get("type", "evidence"))
            src = ev.get("source_name") or ev.get("source") or f"item {i}"
        else:
            etype = str(getattr(ev, "type", "evidence"))
            src = getattr(ev, "source_name", None) or f"item {i}"
        links.append({"index": str(i), "type": etype, "source": str(src)})
    return links


def render_html(report: GapReport, evidence: Iterable[Any] | None = None) -> str:
    """Render a clean, auditor-facing HTML report (score + per-control status)."""
    s = report.summary
    score = s.get("readiness_score", 0)
    as_of = s.get("as_of", "n/a")
    window = s.get("freshness_window_days", 180)
    total = s.get("total", len(report.items))
    satisfied = s.get("satisfied", 0)
    partial = s.get("partial", 0)
    missing = s.get("missing", 0)

    rows: list[str] = []
    for item in sorted(report.items, key=lambda i: (STATUS_ORDER.get(i.status, 3), i.control_id)):
        age = str(item.evidence_age_days) if item.evidence_age_days is not None else "—"
        obligations = ", ".join(item.obligation_ids) if item.obligation_ids else "—"
        badge = {
            "satisfied": "badge badge-ok",
            "partial": "badge badge-warn",
            "missing": "badge badge-bad",
        }.get(item.status, "badge")
        rows.append(
            "<tr>"
            f"<td class='mono'>{html.escape(item.control_id)}</td>"
            f"<td>{html.escape(item.control_name)}</td>"
            f"<td>{html.escape(obligations)}</td>"
            f"<td><span class='{badge}'>{html.escape(STATUS_LABEL.get(item.status, item.status))}</span></td>"
            f"<td class='num'>{html.escape(age)}</td>"
            f"<td>{html.escape(item.remediation_hint or '')}</td>"
            "</tr>"
        )

    ev_links = _evidence_links(report, evidence)
    ev_html = (
        "<section class='evidence'><h2>Evidence</h2><ul>"
        + "".join(
            f"<li>#{e['index']} <span class='mono'>{html.escape(e['type'])}</span> — "
            f"{html.escape(e['source'])}</li>"
            for e in ev_links
        )
        + "</ul></section>"
        if ev_links
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ActReady Gap Report</title>
<style>
  :root {{ --ok:#15803d; --warn:#b45309; --bad:#b91c1c; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; }}
  body {{ font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; color:var(--ink); margin:32px; }}
  h1 {{ margin:0 0 4px; }}
  .meta {{ color:var(--muted); margin-bottom:20px; }}
  .score {{ font-size:34px; font-weight:700; }}
  .strip {{ display:flex; gap:18px; margin:14px 0 22px; }}
  .strip div {{ border:1px solid var(--line); border-radius:8px; padding:8px 14px; }}
  table {{ border-collapse:collapse; width:100%; margin-bottom:24px; }}
  th,td {{ border-bottom:1px solid var(--line); padding:7px 9px; text-align:left; vertical-align:top; }}
  th {{ background:#f8fafc; font-size:12px; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .num {{ text-align:right; }}
  .badge {{ display:inline-block; padding:1px 8px; border-radius:999px; font-size:12px; font-weight:600; color:#fff; }}
  .badge-ok {{ background:var(--ok); }} .badge-warn {{ background:var(--warn); }} .badge-bad {{ background:var(--bad); }}
  .evidence li {{ margin:2px 0; }}
  footer {{ color:var(--muted); font-size:12px; border-top:1px solid var(--line); padding-top:10px; margin-top:8px; }}
  a {{ color:#2563eb; }}
</style>
</head>
<body>
  <h1>ActReady Gap Report</h1>
  <div class="meta">As of {html.escape(str(as_of))} &middot; Freshness window: {html.escape(str(window))} days</div>
  <div class="score">{html.escape(str(score))}<span style="font-size:16px;color:var(--muted)">/100</span></div>
  <div class="strip">
    <div><strong>{total}</strong> controls</div>
    <div><span class="badge badge-ok">Satisfied {satisfied}</span></div>
    <div><span class="badge badge-warn">Partial {partial}</span></div>
    <div><span class="badge badge-bad">Missing {missing}</span></div>
  </div>
  <table>
    <thead><tr><th>Control</th><th>Name</th><th>Obligations</th><th>Status</th><th class="num">Evidence age (d)</th><th>Remediation hint</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  {ev_html}
  <footer>
    Controls mapped from {html.escape(ISO42001_CITATION)} (ISO 42001, Annex A, condensed).
    Obligations from EU AI Act (Regulation (EU) 2024/1689), Articles 9–15:
    <a href="{EURLEX_BASE_URL}">EUR-Lex</a>.
    Engineering aid — not legal advice or a certification of conformity.
  </footer>
</body>
</html>"""


def render_pdf(html_doc: str) -> bytes:
    """Render HTML to PDF via WeasyPrint.

    Raises ``WeasyUnavailable`` when WeasyPrint or its native libraries are not
    available, so callers can fall back to serving the HTML with a clear 501.
    """
    if not weasyprint_available():
        raise WeasyUnavailable(
            "PDF rendering unavailable: weasyprint or its native libraries "
            "(cairo/pango/glib) are not installed on this host."
        )
    return weasyprint.HTML(string=html_doc).write_pdf()  # pragma: no cover - needs libs


__all__ = [
    "WeasyUnavailable",
    "weasyprint_available",
    "render_markdown",
    "render_json",
    "render_html",
    "render_pdf",
]
