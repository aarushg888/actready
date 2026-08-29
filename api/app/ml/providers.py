"""Provider seam for the ML-assist layer.

Mirrors the existing ACTREADY_PROVIDER pattern from app/explain.py. Default is
'none' which short-circuits every ML path with zero network calls and zero
imports of instructor / openai / sentence-transformers.

A `FakeProvider` is included for CI: it returns deterministic fixed vectors so
the embedding tests need NO model download. This is the recommended provider for
the test suite and offline demos.

`LocalProvider` (MiniLM) and `OpenAIProvider` are constructed lazily so their
heavy SDKs are only imported when the matching ACTREADY_PROVIDER is selected.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

# Deterministic dimensionality used by the FakeProvider so tests are stable.
FAKE_DIM = 64


def get_provider_name() -> str:
    """Resolve the ML provider from ACTREADY_PROVIDER (default 'none')."""
    return os.environ.get("ACTREADY_PROVIDER", "none").strip().lower()


@runtime_checkable
class Provider(Protocol):
    """Embedding + extraction seam. Implementations: None/Local/OpenAI/Fake."""

    name: str
    requires_key: bool

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text."""
        ...

    def extract(self, text: str, schema: type[Any]) -> Any:
        """Return a populated pydantic model of `schema` from `text`."""
        ...


@dataclass
class NoneProvider:
    """Default provider. Embeds -> empty, extracts -> raises.

    The deterministic engine is the system of record; with provider 'none' the
    ML layer produces no suggestions and extracts nothing.
    """

    name: str = "none"
    requires_key: bool = False

    def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    def extract(self, text: str, schema: type[Any]) -> Any:
        raise NotImplementedError(
            "NoneProvider cannot extract; set ACTREADY_PROVIDER to 'local' or 'openai'."
        )


@dataclass
class FakeProvider:
    """Deterministic provider for CI / offline tests. No model download.

    Vectors are a stable hash of each text, normalized to unit length, so that
    identical strings are identical vectors and related strings are near. This
    is enough to exercise top-k retrieval deterministically.
    """

    name: str = "fake"
    requires_key: bool = False
    dim: int = FAKE_DIM

    def _vector(self, text: str) -> list[float]:
        # Hashed bag-of-words: each token contributes +1/-1 to a hashed dim, so
        # cosine similarity reflects lexical overlap. Deterministic, no download,
        # and makes top-k retrieval over the catalogs meaningful in tests.
        vec = [0.0] * self.dim
        tokens = [t.lower() for t in text.replace(".", " ").split() if t]
        if not tokens:
            return vec
        for tok in tokens:
            h = int.from_bytes(hashlib.sha256(tok.encode("utf-8")).digest()[:8], "big")
            dim = h % self.dim
            sign = 1.0 if (h & 1) == 0 else -1.0
            vec[dim] += sign
        # L2 normalize so cosine == dot product.
        norm = sum(v * v for v in vec) ** 0.5
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def extract(self, text: str, schema: type[Any]) -> Any:
        raise NotImplementedError("FakeProvider does not perform LLM extraction.")


@dataclass
class LocalProvider:
    """Local, no-key provider: MiniLM for embed, ollama+instructor for extract.

    Heavy deps (sentence-transformers, instructor, openai client) are imported
    lazily on first embed()/extract() call so the default 'none' path — and all
    import-time checks — never load them.
    """

    name: str = "local"
    requires_key: bool = False
    _model: Any = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            model_name = os.environ.get("ACTREADY_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            self._model = SentenceTransformer(model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        # normalize_embeddings gives unit vectors -> cosine == dot.
        vecs = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [v.tolist() for v in vecs]

    def extract(self, text: str, schema: type[Any]) -> Any:
        import instructor  # noqa: PLC0415
        from openai import OpenAI  # noqa: PLC0415

        base_url = os.environ.get("ACTREADY_OLLAMA_URL", "http://localhost:11434/v1")
        client = instructor.from_openai(OpenAI(base_url=base_url, api_key="ollama"))
        return client.chat.completions.create(
            model=os.environ.get("ACTREADY_MODEL", "llama3.2"),
            response_model=schema,
            messages=[{"role": "user", "content": text}],
        )


@dataclass
class OpenAIProvider:
    """Cloud provider (opt-in). Never used unless ACTREADY_PROVIDER=openai."""

    name: str = "openai"
    requires_key: bool = True
    _client: Any = None

    def __post_init__(self) -> None:
        import instructor  # noqa: PLC0415
        from openai import OpenAI  # noqa: PLC0415

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for ACTREADY_PROVIDER=openai")
        self._client = instructor.from_openai(OpenAI())

    def embed(self, texts: list[str]) -> list[list[float]]:
        import openai  # noqa: PLC0415

        resp = openai.embeddings.create(
            model=os.environ.get("ACTREADY_EMBED_MODEL", "text-embedding-3-small"),
            input=texts,
        )
        return [d.embedding for d in resp.data]

    def extract(self, text: str, schema: type[Any]) -> Any:
        return self._client.chat.completions.create(
            model=os.environ.get("ACTREADY_MODEL", "gpt-4o-mini"),
            response_model=schema,
            messages=[{"role": "user", "content": text}],
        )


_PROVIDERS: dict[str, type[Any]] = {
    "none": NoneProvider,
    "fake": FakeProvider,
    "local": LocalProvider,
    "openai": OpenAIProvider,
}


def get_provider(name: str | None = None) -> Provider:
    """Return the selected Provider instance (default from env)."""
    key = name or get_provider_name()
    if key not in _PROVIDERS:
        raise ValueError(f"unknown ACTREADY_PROVIDER {key!r}; expected one of {sorted(_PROVIDERS)}")
    return _PROVIDERS[key]()


__all__ = [
    "FAKE_DIM",
    "Provider",
    "NoneProvider",
    "FakeProvider",
    "LocalProvider",
    "OpenAIProvider",
    "get_provider_name",
    "get_provider",
]
