"""Provider real-path tests with mocked heavy SDKs (no model download / no keys)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from app.ml.providers import LocalProvider, OpenAIProvider


class FakeSTModel:
    def encode(self, texts, normalize_embeddings=False, convert_to_numpy=False):
        import numpy as np

        return np.array([[0.5, 0.5] for _ in texts])


@pytest.fixture
def mock_st(monkeypatch: pytest.MonkeyPatch) -> None:
    # Prevent any real sentence_transformers import; inject a fake model loader.
    import app.ml.providers as prov

    monkeypatch.setattr(prov.LocalProvider, "_ensure_model", lambda self: FakeSTModel())


class TestLocalProviderMocked:
    def test_embed_returns_vectors(self, mock_st: None) -> None:
        p = LocalProvider()
        vecs = p.embed(["risk management", "ai policy"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 2

    def test_extract_uses_instructor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = {"ok": True}
        import instructor
        import openai

        monkeypatch.setattr(instructor, "from_openai", lambda c: fake_client)
        monkeypatch.setattr(openai, "OpenAI", lambda *a, **k: object())
        p = LocalProvider()
        out = p.extract("text", dict)
        assert out == {"ok": True}
        fake_client.chat.completions.create.assert_called_once()


class TestOpenAIProviderMocked:
    def test_embed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import openai as oa

        resp = MagicMock()
        resp.data = [MagicMock(embedding=[0.1, 0.2]), MagicMock(embedding=[0.3, 0.4])]
        monkeypatch.setattr(oa, "embeddings", MagicMock(create=MagicMock(return_value=resp)))
        monkeypatch.setenv("OPENAI_API_KEY", "x")
        import instructor
        import openai

        monkeypatch.setattr(instructor, "from_openai", lambda c: MagicMock())
        monkeypatch.setattr(openai, "OpenAI", lambda *a, **k: object())
        p = OpenAIProvider()
        vecs = p.embed(["a", "b"])
        assert vecs == [[0.1, 0.2], [0.3, 0.4]]

    def test_extract(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = {"extracted": 1}
        monkeypatch.setenv("OPENAI_API_KEY", "x")
        import instructor
        import openai

        monkeypatch.setattr(instructor, "from_openai", lambda c: fake_client)
        monkeypatch.setattr(openai, "OpenAI", lambda *a, **k: object())
        p = OpenAIProvider()
        out = p.extract("text", dict)
        assert out == {"extracted": 1}


class TestRouter:
    def test_healthz_returns_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.ml.router import router

        monkeypatch.setenv("ACTREADY_PROVIDER", "none")
        fast = FastAPI()
        fast.include_router(router)
        client = TestClient(fast)
        res = client.get("/healthz")
        assert res.status_code == 200
        assert res.json()["provider"] == "none"
