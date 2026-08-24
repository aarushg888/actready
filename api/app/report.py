"""Render a GapReport as markdown."""

from __future__ import annotations

from app.models import GapReport

STATUS_ORDER = {"missing": 0, "partial": 1, "satisfied": 2}

EURLEX_BASE_URL = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
ISO42001_CITATION = "ISO/IEC 42001:2023, Information technology — Artificial intelligence — Management system"


def render_markdown(report: GapReport) -> str:
    """Render the gap report: scorecard table, gaps worst-first, standards footer."""
    s = report.summary
    lines: list[str] = []
    lines.append("# ActReady Gap Report")
    lines.append("")
    lines.append(
        f"**Readiness score:** {s.get('readiness_score', 0)}/100 &nbsp;|&nbsp; "
        f"**As of:** {s.get('as_of', 'n/a')} &nbsp;|&nbsp; "
        f"Freshness window: {s.get('freshness_window_days', 180)} days"
    )
    lines.append("")
    lines.append(
        f"{s.get('total', 0)} controls assessed — "
        f"✅ {s.get('satisfied', 0)} satisfied · "
        f"🟡 {s.get('partial', 0)} partial · "
        f"🔴 {s.get('missing', 0)} missing"
    )
    lines.append("")
    lines.append("| Control | Name | Obligations | Status | Evidence age (d) | Remediation hint |")
    lines.append("|---|---|---|---|---|---|")

    items = sorted(report.items, key=lambda i: (STATUS_ORDER.get(i.status, 3), i.control_id))
    for item in items:
        age = str(item.evidence_age_days) if item.evidence_age_days is not None else "—"
        obligations = ", ".join(item.obligation_ids) if item.obligation_ids else "—"
        lines.append(
            f"| {item.control_id} | {item.control_name} | {obligations} "
            f"| {item.status} | {age} | {item.remediation_hint} |"
        )

    lines.append("")
    lines.append("## Scope & citations")
    lines.append("")
    lines.append(f"- Controls mapped from {ISO42001_CITATION} (“ISO 42001”, Annex A, condensed).")
    lines.append(
        f"- Obligations from EU AI Act (Regulation (EU) 2024/1689), Articles 9-15: "
        f"[EUR-Lex base regulation]({EURLEX_BASE_URL})."
    )
    lines.append(
        "- This report is an engineering aid, not legal advice or a certification of conformity."
    )
    return "\n".join(lines)
