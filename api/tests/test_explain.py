"""Tests for L explanations — provider selection via ACTREADY_PROVIDER, zero network in tests."""

from __future__ import annotations

import sys

import pytest

from app.explain import ExplainItem, explain_gaps
from app.mapper import map_evidence


class FakeLLM:
    """Canned structured-output provider; never touches the network."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, prompt: str) -> list[ExplainItem]:
        self.calls += 1
        return [
            ExplainItem(
                control_id="A.5.1",
                why_it_matters="Auditors read the policy first; it anchors every other control.",
                suggested_next_step="Draft an AI policy with owner sign-off and a 12-month review cycle.",
            )
        ]


class TestProviderSelection:
    def test_default_provider_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ACTREADY_PROVIDER", raising=False)
        from app import explain

        assert explain.get_provider() == "none"

    def test_env_selects_fake(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACTREADY_PROVIDER", "fake")
        from app import explain

        assert explain.get_provider() == "fake"

    def test_none_returns_empty_without_llm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ACTREADY_PROVIDER", raising=False)
        report = map_evidence([])
        items = explain_gaps(report)
        assert items == []

    def test_fake_provider_returns_canned_items(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = FakeLLM()
        monkeypatch.setenv("ACTREADY_PROVIDER", "fake")
        report = map_evidence([])
        items = explain_gaps(report, llm=fake)
        assert len(items) == 1
        assert items[0].control_id == "A.5.1"
        assert fake.calls == 1

    def test_unknown_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACTREADY_PROVIDER", "skynet")
        report = map_evidence([])
        with pytest.raises(ValueError):
            explain_gaps(report)


class TestNoNetworkImports:
    def test_openai_not_imported_when_provider_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ACTREADY_PROVIDER", raising=False)
        for mod in ("openai", "instructor"):
            sys.modules.pop(mod, None)
        explain_gaps(map_evidence([]))
        assert "openai" not in sys.modules, "openai must be lazily imported only when provider != none"
        assert "instructor" not in sys.modules
