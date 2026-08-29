"""Evidence -> control suggestion (the ML-1 feature).

Given free-text evidence, propose the controls / obligations it bears on via
cosine top-k over the control embedding index. Each suggestion carries a
similarity, a heuristic confidence, and the grounded source chunk so a
faithfulness pre-check can drop ungrounded suggestions.

SAFETY: suggestions are *never* auto-applied. They are returned to the caller
for human review and confirmation. This routine must not mutate control
mappings or the deterministic engine state.
"""

from __future__ import annotations

from app.ml.embed import ControlIndex, ControlRecord
from app.ml.schemas import Suggestion


# Heuristic confidence = cosine similarity rescaled into 0..1 (already 0..1 for
# unit vectors). Pure cosine is the v0.2 default; a bge-reranker score can be
# blended in ml-plan §2 but is optional and degrades gracefully.
def _heuristic_confidence(similarity: float) -> float:
    return max(0.0, min(1.0, float(similarity)))


def faithfulness_precheck(query: str, record: ControlRecord, similarity: float) -> bool:
    """RAGAS-style grounding pre-check (stub).

    TODO(ML): wire a real RAGAS Faithfulness/ContextRecall evaluator here. For
    v0.2 the mechanical check is: the suggestion is grounded iff the retrieved
    control's text shares at least one salient token with the evidence query
    AND similarity clears a floor. This prevents "no retrievable grounding"
    suggestions from shipping (ml-plan §1 / C2).
    """
    floor = 0.05
    if similarity < floor:
        return False
    q_tokens = {t for t in query.lower().split() if len(t) > 3}
    c_tokens = {t for t in record.text.lower().split() if len(t) > 3}
    # grounded when the query and the control share vocabulary (cheap proxy)
    return bool(q_tokens & c_tokens)


def suggest_controls(
    evidence_text: str,
    index: ControlIndex,
    k: int = 5,
    provider_name: str = "none",
) -> list[Suggestion]:
    """Return up to k control Suggestions for the evidence text.

    Never mutates control mappings. Returns [] when the provider is 'none'
    (deterministic short-circuit) or the text is empty.
    """
    if not evidence_text or not evidence_text.strip():
        return []
    if provider_name == "none":
        # Deterministic engine is the system of record; no proposals.
        return []

    results = index.top_k_similar(evidence_text, k=k)
    suggestions: list[Suggestion] = []
    for record, sim in results:
        grounded = faithfulness_precheck(evidence_text, record, sim)
        suggestions.append(
            Suggestion(
                control_id=record.id,
                similarity=round(sim, 6),
                confidence=round(_heuristic_confidence(sim), 6),
                source_chunk=record.description,
                citation=f"{record.catalog}:{record.id}",
                control_name=record.name,
                grounded=grounded,
            )
        )
    return suggestions


__all__ = ["suggest_controls", "faithfulness_precheck"]
