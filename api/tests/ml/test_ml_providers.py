"""Provider seam tests: None/Fake/Local selection + zero network imports."""

from __future__ import annotations

import sys

import pytest

from app.ml.providers import (
    FakeProvider,
    LocalProvider,
    NoneProvider,
    OpenAIProvider,
    get_provider,
    get_provider_name,
)


class TestProviderSelection:
    def test_default_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ACTREADY_PROVIDER", raising=False)
        assert get_provider_name() == "none"

    def test_fake_selected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACTREADY_PROVIDER", "fake")
        assert isinstance(get_provider(), FakeProvider)

    def test_none_selected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACTREADY_PROVIDER", "none")
        assert isinstance(get_provider(), NoneProvider)

    def test_unknown_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACTREADY_PROVIDER", "skynet")
        with pytest.raises(ValueError):
            get_provider()


class TestNoneProvider:
    def test_embed_returns_empty(self) -> None:
        assert NoneProvider().embed(["a", "b"]) == []

    def test_extract_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            NoneProvider().extract("x", dict)


class TestFakeProvider:
    def test_deterministic(self) -> None:
        p = FakeProvider()
        a = p.embed(["risk management system"])
        b = p.embed(["risk management system"])
        assert a == b
        assert len(a[0]) == FakeProvider().dim

    def test_different_texts_differ(self) -> None:
        p = FakeProvider()
        a, b = p.embed(["alpha governance policy", "totally unrelated zebra quark"])
        assert a != b

    def test_unit_norm(self) -> None:
        import math

        p = FakeProvider()
        (v,) = p.embed(["normalize me"])
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-9

    def test_extract_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            FakeProvider().extract("x", dict)


class TestLazyImports:
    def test_openai_not_imported_when_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ACTREADY_PROVIDER", raising=False)
        for mod in ("openai", "instructor", "sentence_transformers"):
            sys.modules.pop(mod, None)
        get_provider()  # none
        assert "openai" not in sys.modules
        assert "instructor" not in sys.modules
        assert "sentence_transformers" not in sys.modules

    def test_local_provider_selectable_without_import(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACTREADY_PROVIDER", "local")
        # get_provider() should NOT trigger the sentence_transformers import;
        # the heavy SDK is only pulled on first embed() call.
        for mod in ("sentence_transformers",):
            sys.modules.pop(mod, None)
        prov = get_provider()
        assert isinstance(prov, LocalProvider)
        # No embed() called -> heavy SDK not imported.
        assert "sentence_transformers" not in sys.modules

    def test_openai_provider_constructor_requires_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACTREADY_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError):
            OpenAIProvider()
