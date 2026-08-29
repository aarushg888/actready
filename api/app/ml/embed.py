"""Control-embedding index + top-k retrieval.

Builds a vector index over the curated control/obligation catalogs
(data/controls_iso42001.yaml + data/obligations_eu_ai_act.yaml) and answers
'which controls does this evidence bear on?' via cosine top-k.

Storage backends:
  - InMemoryVectorStore (default for tests / no-PG): a Chroma-like dict. Works
    with the FakeProvider so CI needs NO model download.
  - PgVectorStore (optional): persists into Postgres via pgvector when a DSN is
    available. Same retrieval semantics.

The deterministic engine stays the system of record; this index only *proposes*.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pgvector.sqlalchemy import Vector  # noqa: F401 — used by PgVectorStore
from sqlalchemy import (
    Column,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    insert,
    select,
)

from app.ml.providers import Provider, get_provider


@dataclass
class ControlRecord:
    """A single embeddable control/obligation clause."""

    id: str
    name: str
    description: str
    catalog: str  # "iso42001" | "eu_ai_act"
    vector: list[float] | None = None

    @property
    def text(self) -> str:
        return f"{self.id}: {self.name}. {self.description}"


def load_control_records(data_dir: str | None = None) -> list[ControlRecord]:
    """Load controls + obligations from the YAML catalogs into ControlRecords."""
    from app.catalog import DEFAULT_DATA_DIR as CATALOG_DIR
    from app.catalog import load_controls, load_obligations

    base = data_dir or CATALOG_DIR
    records: list[ControlRecord] = []
    for c in load_controls(base):
        records.append(
            ControlRecord(id=c.id, name=c.name, description=c.description, catalog="iso42001")
        )
    for o in load_obligations(base):
        records.append(
            ControlRecord(
                id=o.id,
                name=o.title,
                description=o.description,
                catalog="eu_ai_act",
            )
        )
    return records


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Storage backends
# ---------------------------------------------------------------------------

@dataclass
class InMemoryVectorStore:
    """Chroma-like in-memory cosine store. No external deps, CI-friendly."""

    records: list[ControlRecord] = field(default_factory=list)
    dim: int | None = None

    def add(self, records: list[ControlRecord]) -> None:
        self.records.extend(records)
        for r in records:
            if r.vector:
                self.dim = len(r.vector)

    def top_k(self, query_vec: list[float], k: int) -> list[tuple[ControlRecord, float]]:
        scored = [(r, _cosine(query_vec, r.vector or [])) for r in self.records if r.vector]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


@dataclass
class PgVectorStore:
    """pgvector-backed store.

    NOTE: this path imports sqlalchemy + pgvector at module load (both are now
    declared dependencies). It is only constructed by ControlIndex.build when a
    DSN is supplied; the default test path uses InMemoryVectorStore and never
    instantiates this class.
    """

    dsn: str
    table: str = "ml_control_embeddings"
    dim: int = 384
    _engine: Any = None

    def _get_engine(self) -> Any:
        if self._engine is None:
            self._engine = create_engine(self.dsn, future=True)
        return self._engine

    def _table(self) -> Table:
        return Table(
            self.table,
            MetaData(),
            Column("id", String, primary_key=True),
            Column("name", String),
            Column("catalog", String),
            Column("description", Text),
            Column("embedding", Vector(self.dim)),
        )

    def add(self, records: list[ControlRecord]) -> None:
        engine = self._get_engine()
        table = self._table()
        metadata = table.metadata
        metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(delete(table))
            for r in records:
                conn.execute(
                    insert(table).values(
                        id=r.id,
                        name=r.name,
                        catalog=r.catalog,
                        description=r.description,
                        embedding=r.vector,
                    )
                )

    def top_k(self, query_vec: list[float], k: int) -> list[tuple[ControlRecord, float]]:
        engine = self._get_engine()
        table = self._table()
        with engine.connect() as conn:
            stmt = select(
                table.c.id,
                table.c.name,
                table.c.catalog,
                table.c.description,
                1.0 - table.c.embedding.cosine_distance(query_vec).label("similarity"),
            ).order_by(table.c.embedding.cosine_distance(query_vec)).limit(k)
            rows = conn.execute(stmt).all()
        return [
            (
                ControlRecord(id=row[0], name=row[1], catalog=row[2], description=row[3]),
                float(row[4]),
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Index (build once, reuse)
# ---------------------------------------------------------------------------

class ControlIndex:
    """Embeds control records and answers top-k similarity queries."""

    def __init__(self, store: InMemoryVectorStore | PgVectorStore, provider: Provider):
        self.store = store
        self.provider = provider

    @classmethod
    def build(
        cls,
        data_dir: str | None = None,
        provider: Provider | None = None,
        store: InMemoryVectorStore | PgVectorStore | None = None,
        dsn: str | None = None,
    ) -> ControlIndex:
        provider = provider or get_provider()
        records = load_control_records(data_dir)
        texts = [r.text for r in records]
        vectors = provider.embed(texts)
        for r, v in zip(records, vectors, strict=False):
            r.vector = v

        if store is None:
            if dsn is not None:
                dim = len(vectors[0]) if vectors else 384
                store = PgVectorStore(dsn=dsn, dim=dim)
            else:
                store = InMemoryVectorStore()
        store.add(records)
        return cls(store=store, provider=provider)

    def top_k_similar(self, control_query: str, k: int = 5) -> list[tuple[ControlRecord, float]]:
        """Return up to k (record, similarity) pairs for a free-text query."""
        if not control_query or not control_query.strip():
            return []
        (qv,) = self.provider.embed([control_query])
        return self.store.top_k(qv, k)


__all__ = [
    "ControlRecord",
    "InMemoryVectorStore",
    "PgVectorStore",
    "ControlIndex",
    "load_control_records",
]
