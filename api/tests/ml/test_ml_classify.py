"""classify.suggest_controls tests: returns Suggestion list, never mutates."""

from __future__ import annotations

import pytest

from app.ml.classify import faithfulness_precheck, suggest_controls
from app.ml.embed import ControlIndex, InMemoryVectorStore
from app.ml.providers import FakeProvider
from app.ml.schemas import Suggestion


def _index() -> ControlIndex:
    store = InMemoryVectorStore()
    return ControlIndex.build(provider=FakeProvider(), store=store)


class TestSuggestControls:
    def test_none_provider_returns_empty(self, fake_index: ControlIndex) -> None:
        # provider_name 'none' short-circuits regardless of index.
        out = suggest_controls("risk management system", index=fake_index, provider_name="none")
        assert out == []

    def test_fake_provider_returns_suggestions(self, fake_index: ControlIndex) -> None:
        out = suggest_controls(
            "Documented, approved, communicated AI policy including scope and "
            "commitment to responsible AI development and use.",
            index=fake_index,
            k=5,
            provider_name="fake",
        )
        assert len(out) > 0
        assert all(isinstance(s, Suggestion) for s in out)
        # sorted by similarity desc, confidence defined
        for s in out:
            assert 0.0 <= s.confidence <= 1.0
            assert 0.0 <= s.similarity <= 1.0

    def test_empty_text_returns_empty(self, fake_index: ControlIndex) -> None:
        assert suggest_controls("", index=fake_index, provider_name="fake") == []

    def test_suggestions_have_citation_and_chunk(self, fake_index: ControlIndex) -> None:
        out = suggest_controls(
            "AI policy document", index=fake_index, k=3, provider_name="fake"
        )
        for s in out:
            assert s.citation
            assert s.control_id

    def test_does_not_mutate_index(self, fake_index: ControlIndex) -> None:
        before = len(fake_index.store.records)
        suggest_controls("AI policy document", index=fake_index, k=5, provider_name="fake")
        # calling suggest must not add/remove control records
        assert len(fake_index.store.records) == before


class TestFaithfulnessPrecheck:
    def test_drop_on_low_similarity(self, fake_index: ControlIndex) -> None:
        rec = fake_index.store.records[0]
        assert faithfulness_precheck("zzz qqq", rec, similarity=0.01) is False

    def test_grounded_on_shared_tokens(self, fake_index: ControlIndex) -> None:
        rec = next(r for r in fake_index.store.records if r.id == "A.5.1")
        ok = faithfulness_precheck(
            "Documented AI policy and governance", rec, similarity=0.5
        )
        assert ok is True
