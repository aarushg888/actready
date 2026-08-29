"""Pytest fixtures for the ML-assist suite (isolated from the engine/PG conftest).

Keeps ACTREADY_PROVIDER='none' by default so the suite makes zero network calls
and zero heavy SDK imports. Tests that need a real embedder use FakeProvider
(deterministic, no download, no model weights).
"""

from __future__ import annotations

import pytest

from app.ml.embed import ControlIndex, InMemoryVectorStore
from app.ml.providers import FakeProvider


@pytest.fixture(autouse=True)
def _default_none_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACTREADY_PROVIDER", "none")


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def fake_index(fake_provider: FakeProvider) -> ControlIndex:
    """Control index built from the real catalogs using FakeProvider (no download)."""
    store = InMemoryVectorStore()
    return ControlIndex.build(provider=fake_provider, store=store)
