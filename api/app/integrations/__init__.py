"""Integration adapters for ActReady v0.2 (M2).

Exposes the EvidenceSource Protocol, the per-source isolation wrapper, and the
GitHub App + promptfoo/deepeval CI-push adapters. Routers live under
``app.routers`` and are wired into the FastAPI app by the gateway layer.

Wiring note for the human/M1 handoff:
    In ``app/main.py`` add (guarded so a missing module never breaks bring-up)::

        try:
            from app.routers.integrations import router as integrations_router
            app.include_router(integrations_router)
            from app.integrations.eval_push import router as eval_router
            app.include_router(eval_router)
        except Exception:  # pragma: no cover - defensive wiring
            pass
"""

from app.integrations.base import EvidenceSource, run_isolated
from app.integrations.types import RawEvidence

__all__ = ["EvidenceSource", "RawEvidence", "run_isolated"]
