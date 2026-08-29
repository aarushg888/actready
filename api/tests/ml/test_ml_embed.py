"""Embedding index + top-k retrieval tests (FakeProvider, no download)."""

from __future__ import annotations

import pytest

from app.ml.embed import ControlIndex, InMemoryVectorStore, load_control_records
from app.ml.providers import FakeProvider


class TestControlRecords:
    def test_loads_controls_and_obligations(self) -> None:
        recs = load_control_records()
        ids = {r.id for r in recs}
        assert "A.5.1" in ids
        assert "EUAI-ART-9-1" in ids
        assert any(r.catalog == "iso42001" for r in recs)
        assert any(r.catalog == "eu_ai_act" for r in recs)

    def test_text_includes_id_name_description(self) -> None:
        recs = load_control_records()
        a51 = next(r for r in recs if r.id == "A.5.1")
        assert "A.5.1" in a51.text and "Policies" in a51.text


class TestInMemoryStore:
    def test_top_k_returns_requested_count(self) -> None:
        p = FakeProvider()
        recs = load_control_records()
        for r, v in zip(recs, p.embed([r.text for r in recs])):
            r.vector = v
        store = InMemoryVectorStore()
        store.add(recs)
        (qv,) = p.embed(["AI policy document"])
        top = store.top_k(qv, k=3)
        assert len(top) == 3
        # sorted descending by similarity
        sims = [s for _, s in top]
        assert sims == sorted(sims, reverse=True)

    def test_top_k_empty_when_no_vectors(self) -> None:
        store = InMemoryVectorStore()
        (qv,) = FakeProvider().embed(["x"])
        assert store.top_k(qv, k=5) == []


class TestControlIndex:
    def test_build_with_fake_provider(self, fake_index: ControlIndex) -> None:
        assert isinstance(fake_index.store, InMemoryVectorStore)
        assert len(fake_index.store.records) > 0

    def test_top_k_similar_known_query(self, fake_index: ControlIndex) -> None:
        # Query text overlapping with A.5.1's description should surface it
        # near the top (FakeProvider hashes text -> near vectors for overlap).
        results = fake_index.top_k_similar(
            "Documented, approved, communicated AI policy including scope and "
            "commitment to responsible AI development and use.", k=5
        )
        assert len(results) > 0
        ids = [r.id for r, _ in results]
        assert "A.5.1" in ids

    def test_top_k_empty_query(self, fake_index: ControlIndex) -> None:
        assert fake_index.top_k_similar("", k=5) == []

    def test_similarity_in_unit_range(self, fake_index: ControlIndex) -> None:
        results = fake_index.top_k_similar("risk management system lifecycle", k=3)
        for _, sim in results:
            assert -1.0 <= sim <= 1.0
