"""SQLAlchemy model + helpers for the append-only, hash-chained ML proposal log.

Mirrors the immutability discipline of `evidence_artifacts` (backend-plan §3.2,
ARCHITECTURE.md invariant #2). Each proposal stores `prev_hash` (the prior
row's own_hash) and `own_hash` (sha256 over its own payload + prev_hash), forming
a tamper-evident chain. A `parent_evidence_hash` links each proposal to the
exact artifact version it derived from so an ISO 42001 auditor can replay
proposal -> human -> confirmed.

TESTS create these tables via metadata.create_all so they pass even before M1's
models_db.py lands and before Alembic migrations exist.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (  # noqa: F401 — re-exported for tests
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates

GENESIS_HASH = "0" * 64  # prev_hash of the first row in any chain


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_fields(row: MLProposal, payload: dict[str, Any]) -> dict[str, Any]:
    """Stable field set covered by the hash (excludes the timestamp, which can
    change representation on DB round-trip and would break verification)."""
    return {
        "tenant_id": row.tenant_id,
        "proposal_type": row.proposal_type,
        "control_id": row.control_id,
        "evidence_ref": row.evidence_ref,
        "parent_evidence_hash": row.parent_evidence_hash,
        "payload": payload,
        "confidence": row.confidence,
        "status": row.status,
        "prev_hash": row.prev_hash,
    }


def compute_own_hash(prev_hash: str, fields: dict[str, Any]) -> str:
    """sha256 over a stable field dict (canonical JSON). Deterministic + stable."""
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)
    blob = f"{prev_hash}|{canonical}".encode()
    return hashlib.sha256(blob).hexdigest()


class MLProposal(Base):
    """Append-only, hash-chained ML proposal row. NEVER updated or deleted."""

    __tablename__ = "ml_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    proposal_type: Mapped[str] = mapped_column(String(32))  # suggestion | extraction
    control_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[str] = mapped_column(Text)  # JSON-encoded proposal content
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    prev_hash: Mapped[str] = mapped_column(String(64), default=GENESIS_HASH)
    own_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    @validates("payload")
    def _validate_payload(self, key: str, value: Any) -> Any:
        # payload must be JSON-serializable text
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, default=str)
        return value

    def to_payload_dict(self) -> dict[str, Any]:
        # Exposed for debugging/audit; not used in hashing.
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "proposal_type": self.proposal_type,
            "control_id": self.control_id,
            "evidence_ref": self.evidence_ref,
            "parent_evidence_hash": self.parent_evidence_hash,
            "payload": self.payload,
            "confidence": self.confidence,
            "status": self.status,
            "prev_hash": self.prev_hash,
            "own_hash": self.own_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def recompute_own_hash(self) -> str:
        payload = json.loads(self.payload) if isinstance(self.payload, str) else self.payload
        return compute_own_hash(self.prev_hash, _hash_fields(self, payload))


def append_proposal(
    session: Any,
    *,
    tenant_id: str,
    proposal_type: str,
    payload: dict[str, Any],
    control_id: str | None = None,
    evidence_ref: str | None = None,
    parent_evidence_hash: str | None = None,
    confidence: float | None = None,
    status: str = "proposed",
) -> MLProposal:
    """Append a new proposal to the chain for `tenant_id`.

    prev_hash is taken from the most recent proposal for the tenant (or the
    genesis hash if this is the first). Computes and stores own_hash. Returns
    the new row (not yet committed — caller flushes/commits).
    """
    last = (
        session.query(MLProposal)
        .filter(MLProposal.tenant_id == tenant_id)
        .order_by(MLProposal.id.desc())
        .first()
    )
    prev_hash = last.own_hash if last is not None else GENESIS_HASH

    row = MLProposal(
        tenant_id=tenant_id,
        proposal_type=proposal_type,
        control_id=control_id,
        evidence_ref=evidence_ref,
        parent_evidence_hash=parent_evidence_hash,
        payload=json.dumps(payload, sort_keys=True, default=str),
        confidence=confidence,
        status=status,
        prev_hash=prev_hash,
        created_at=_now(),
    )
    # compute own_hash from the stable field set (including prev_hash)
    full = _hash_fields(row, payload)
    row.own_hash = compute_own_hash(prev_hash, full)
    session.add(row)
    return row


def verify_chain(session: Any, tenant_id: str | None = None) -> bool:
    """Return True if every row's own_hash matches its recomputed value AND each
    row's prev_hash equals the prior row's own_hash (linked list intact)."""
    q = session.query(MLProposal).order_by(MLProposal.id.asc())
    if tenant_id is not None:
        q = q.filter(MLProposal.tenant_id == tenant_id)
    rows = q.all()
    expected_prev = GENESIS_HASH
    for r in rows:
        if r.prev_hash != expected_prev:
            return False
        payload = json.loads(r.payload) if isinstance(r.payload, str) else r.payload
        if r.own_hash != compute_own_hash(r.prev_hash, _hash_fields(r, payload)):
            return False
        expected_prev = r.own_hash
    return True


def detect_tamper(session: Any, tenant_id: str | None = None) -> list[int]:
    """Return the ids of any rows whose chain is broken (for audit alerts)."""
    q = session.query(MLProposal).order_by(MLProposal.id.asc())
    if tenant_id is not None:
        q = q.filter(MLProposal.tenant_id == tenant_id)
    rows = q.all()
    bad: list[int] = []
    expected_prev = GENESIS_HASH
    for r in rows:
        payload = json.loads(r.payload) if isinstance(r.payload, str) else r.payload
        full = _hash_fields(r, payload)
        if r.prev_hash != expected_prev or r.own_hash != compute_own_hash(r.prev_hash, full):
            bad.append(r.id)
        expected_prev = r.own_hash
    return bad


__all__ = [
    "Base",
    "MLProposal",
    "GENESIS_HASH",
    "compute_own_hash",
    "append_proposal",
    "verify_chain",
    "detect_tamper",
]
