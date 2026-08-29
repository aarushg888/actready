"""MLProposal hash-chain tests: append, verify, and tamper detection.

Tables are created via metadata.create_all so this passes even before M1's
models_db.py / Alembic migrations exist.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session, sessionmaker

from app.models_ml import (
    GENESIS_HASH,
    Base,
    MLProposal,
    append_proposal,
    compute_own_hash,
    detect_tamper,
    verify_chain,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, future=True)
    with maker() as s:
        yield s


class TestHashChain:
    def test_genesis_prev_is_zero(self) -> None:
        assert GENESIS_HASH == "0" * 64

    def test_append_first_row_links_to_genesis(self, session: Session) -> None:
        row = append_proposal(
            session,
            tenant_id="t1",
            proposal_type="suggestion",
            payload={"control_id": "A.5.1", "confidence": 0.9},
            control_id="A.5.1",
            confidence=0.9,
        )
        assert row.prev_hash == GENESIS_HASH
        assert len(row.own_hash) == 64
        session.flush()
        assert verify_chain(session, tenant_id="t1") is True

    def test_chain_links_consecutive_rows(self, session: Session) -> None:
        for i in range(3):
            append_proposal(
                session,
                tenant_id="t1",
                proposal_type="suggestion",
                payload={"n": i},
            )
        session.flush()
        rows = session.query(MLProposal).order_by(MLProposal.id).all()
        assert rows[0].prev_hash == GENESIS_HASH
        assert rows[1].prev_hash == rows[0].own_hash
        assert rows[2].prev_hash == rows[1].own_hash
        assert verify_chain(session, tenant_id="t1") is True

    def test_tamper_detected(self, session: Session) -> None:
        for i in range(3):
            append_proposal(
                session,
                tenant_id="t1",
                proposal_type="suggestion",
                payload={"n": i},
            )
        session.flush()
        # tamper: mutate a middle row's payload without recomputing hash
        mid = session.query(MLProposal).order_by(MLProposal.id).all()[1]
        mid.payload = '{"n": 999}'
        session.flush()
        assert verify_chain(session, tenant_id="t1") is False
        bad = detect_tamper(session, tenant_id="t1")
        assert mid.id in bad

    def test_tamper_prev_hash_breaks_chain(self, session: Session) -> None:
        for i in range(2):
            append_proposal(
                session,
                tenant_id="t1",
                proposal_type="extraction",
                payload={"n": i},
            )
        session.flush()
        second = session.query(MLProposal).order_by(MLProposal.id).all()[1]
        second.prev_hash = "0" * 64  # break the link
        session.flush()
        assert verify_chain(session, tenant_id="t1") is False

    def test_compute_own_hash_deterministic(self) -> None:
        p = {"a": 1, "b": [1, 2]}
        h1 = compute_own_hash("prev", p)
        h2 = compute_own_hash("prev", p)
        assert h1 == h2
        assert h1 != compute_own_hash("other", p)

    def test_isolated_tenants(self, session: Session) -> None:
        append_proposal(session, tenant_id="t1", proposal_type="suggestion", payload={"x": 1})
        append_proposal(session, tenant_id="t2", proposal_type="suggestion", payload={"x": 2})
        session.flush()
        assert verify_chain(session, tenant_id="t1") is True
        assert verify_chain(session, tenant_id="t2") is True
