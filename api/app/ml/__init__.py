"""ML-assist package.

Lazy imports only — importing this package must not pull in sentence-transformers
/ openai / pgvector unless a provider actually needs them. `get_provider` is the
single seam (mirrors app.explain).
"""

from __future__ import annotations

from app.ml.providers import (
    FakeProvider,
    NoneProvider,
    Provider,
    get_provider,
    get_provider_name,
)
from app.ml.schemas import (
    ExtractionResult,
    FieldWithConf,
    IncidentFields,
    ModelCardFields,
    Suggestion,
)

__all__ = [
    "Provider",
    "NoneProvider",
    "FakeProvider",
    "get_provider",
    "get_provider_name",
    "Suggestion",
    "FieldWithConf",
    "ModelCardFields",
    "IncidentFields",
    "ExtractionResult",
]
