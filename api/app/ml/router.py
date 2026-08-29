"""FastAPI router for the ML-assist layer (proposal endpoints).

NOT auto-wired into app.main. M1 owns main.py and the service layer; this router
is provided ready-to-include so the ML surface can be mounted once the engine
and auth land, behind the ACTREADY_PROVIDER flag.

To enable (after M1 merges), in app/main.py add:

    from app.ml.router import router as ml_router
    app.include_router(ml_router, prefix="/api/ml", tags=["ml"])

All responses are PROPOSALS: the endpoints return suggestions / extractions and
append to the hash-chained ml_proposals log, but they never mutate the
deterministic control_mappings or evidence store. Promotion to real state
requires an explicit human action (see models_ml.append_proposal + a future
confirm endpoint).
"""

from __future__ import annotations

from fastapi import APIRouter

# Example route skeleton (left commented/inert until M1 provides get_principal
# and the session dependency). Shown for documentation; uncomment on wiring.
#
# router = APIRouter()
#
# @router.post("/suggest", response_model=list[Suggestion])
# async def suggest(
#     body: SuggestRequest,
#     principal: Annotated[Principal, Depends(get_principal)],
# ) -> list[Suggestion]:
#     provider = get_provider()
#     if provider.name == "none":
#         return []
#     index = ControlIndex.build(provider=provider)  # cache per tenant in prod
#     suggestions = suggest_controls(body.evidence_text, index=index, k=body.k,
#                                     provider_name=provider.name)
#     # log each as a proposal (human-confirm gated)
#     for s in suggestions:
#         append_proposal(session, tenant_id=principal.tenant_id,
#                         proposal_type="suggestion", control_id=s.control_id,
#                         payload=s.model_dump(), confidence=s.confidence)
#     return suggestions

router = APIRouter()


@router.get("/healthz", tags=["ml"])
def ml_healthz() -> dict[str, str]:
    """Lightweight ML subsystem health — reports the active provider."""
    from app.ml.providers import get_provider_name

    return {"status": "ok", "provider": get_provider_name()}


__all__ = ["router"]
