"""Optional LLM gap explanations. Provider via ACTREADY_PROVIDER env ('none' default).

openai/instructor are imported lazily inside the openai-provider branch only, so the
default path (and the whole test suite) makes zero network calls and zero SDK imports.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from app.models import GapItem, GapReport

ExplainFn = Callable[[str], list["ExplainItem"]]


class ExplainItem(BaseModel):
    control_id: str
    why_it_matters: str = Field(..., description="One-paragraph business rationale for closing this gap.")
    suggested_next_step: str = Field(..., description="Concrete first action the team can take this week.")


def get_provider() -> str:
    """Resolve the explanation provider from ACTREADY_PROVIDER (default 'none')."""
    return os.environ.get("ACTREADY_PROVIDER", "none").strip().lower()


def _prompt_for(items: list[GapItem]) -> str:
    lines = [
        "You are an AI-governance auditor's assistant. For each control gap below,",
        "explain why it matters and suggest one concrete next step.",
        "",
    ]
    for i in items:
        lines.append(f"- {i.control_id} ({i.control_name}) [{i.status}] — {i.remediation_hint}")
    return "\n".join(lines)


def _fake_explain(prompt: str) -> list[ExplainItem]:
    """Deterministic offline stand-in used by tests and demos."""
    return [
        ExplainItem(
            control_id="A.5.1",
            why_it_matters="Auditors read the policy first; it anchors every other control.",
            suggested_next_step="Draft an AI policy with owner sign-off and a 12-month review cycle.",
        )
    ]


def _openai_explain(prompt: str) -> list[ExplainItem]:
    """Real provider path: instructor + OpenAI structured output. Lazy imports on purpose."""
    import instructor  # noqa: PLC0415 — lazy: only when ACTREADY_PROVIDER=openai
    from openai import OpenAI  # noqa: PLC0415 — lazy: only when ACTREADY_PROVIDER=openai

    client = instructor.from_openai(OpenAI())  # reads OPENAI_API_KEY from env
    return client.chat.completions.create(
        model=os.environ.get("ACTREADY_MODEL", "gpt-4o-mini"),
        response_model=list[ExplainItem],
        messages=[{"role": "user", "content": prompt}],
    )


_PROVIDERS: dict[str, ExplainFn | None] = {
    "none": None,
    "fake": _fake_explain,
    "openai": _openai_explain,
}


def explain_gaps(report: GapReport, llm: Any | None = None) -> list[ExplainItem]:
    """Return LLM explanations for the worst gaps. No-op ([]) when provider is 'none'.

    `llm` injects a callable for testing; otherwise the provider is chosen from env.
    """
    provider = get_provider()
    if provider not in _PROVIDERS:
        raise ValueError(f"unknown ACTREADY_PROVIDER {provider!r}; expected one of {sorted(_PROVIDERS)}")
    if provider == "none":
        return []

    fn: ExplainFn | None = llm if llm is not None else _PROVIDERS[provider]
    if fn is None:
        return []

    gaps = [i for i in report.items if i.status != "satisfied"]
    if not gaps:
        return []
    return fn(_prompt_for(gaps[:10]))
