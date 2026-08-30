"""SQLAlchemy 2.0 ORM models for ActReady v0.2 (multi-tenant).

Mirrors the data-model skeletons in ``docs/planning/backend-plan.md §2`` and
``ARCHITECTURE.md``. Tenant-scoped tables carry ``org_id`` (= the RLS tenant
key). RLS policies are applied in a dedicated post-deploy migration
(``migrations/versions/*_enable_rls.py``), not here.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Organization(Base):
    """Tenant. ``id`` is the RLS tenant key; ``plan`` gates feature access."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(32), default="free")  # free|team|scale
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    memberships: Mapped[list[Membership]] = relationship(back_populates="org")


class User(Base):
    """Platform user (auth identity)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Membership(Base):
    """user <-> org with role. ``viewer`` = auditor read-only (v0.4)."""

    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="member")  # owner|admin|member|viewer
    org: Mapped[Organization] = relationship(back_populates="memberships")
    __table_args__ = (UniqueConstraint("org_id", "user_id"),)


class IntegrationConnection(Base):
    """Per-org connector config. ``creds_encrypted`` is envelope-encrypted."""

    __tablename__ = "integration_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # github_app|promptfoo_ci
    creds_encrypted: Mapped[bytes] = mapped_column(LargeBinary)  # never plaintext
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="connected")  # connected|degraded|disconnected
    last_sync: Mapped[dt.datetime | None] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    __table_args__ = (UniqueConstraint("org_id", "type"),)


class EvidenceArtifact(Base):
    """Immutable, tamper-evident. Never UPDATE/DELETE (DB trigger enforces)."""

    __tablename__ = "evidence_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(32))  # model_card|eval_run|incident_log|policy
    source: Mapped[str] = mapped_column(String(255))  # e.g. github:org/repo
    raw_payload: Mapped[dict] = mapped_column(JSON)  # canonicalized
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # sha256(canonical_json)
    manifest_hash: Mapped[str | None] = mapped_column(String(64))  # per-report chain (set on snapshot)
    collected_at: Mapped[dt.date] = mapped_column(Date)  # when the source event happened
    ingested_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    mappings: Mapped[list[ControlMapping]] = relationship(back_populates="artifact")


class ControlMapping(Base):
    """Recomputed by the engine, never hand-edited."""

    __tablename__ = "control_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_artifacts.id"), index=True)
    control_id: Mapped[str] = mapped_column(String(64), index=True)
    obligation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))  # satisfied|partial|missing
    score: Mapped[float | None] = mapped_column(Float)
    catalog_version: Mapped[str] = mapped_column(String(32))
    suggested_by_ml: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    mapped_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    artifact: Mapped[EvidenceArtifact] = relationship(back_populates="mappings")
    __table_args__ = (
        Index(
            "ix_control_mappings_artifact_control",
            "artifact_id",
            "control_id",
        ),
    )


class IngestionRun(Base):
    """Per-source job record; powers health dashboard + idempotency."""

    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    source: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)  # at-least-once dedupe
    status: Mapped[str] = mapped_column(String(16))  # success|partial|failed
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(String(500))  # truncated
    items_ingested: Mapped[int] = mapped_column(default=0)


class ReportSnapshot(Base):
    """Versioned, point-in-time GapReport. Diffable over time."""

    __tablename__ = "report_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    catalog_version: Mapped[str] = mapped_column(String(32))
    manifest_hash: Mapped[str] = mapped_column(String(64))  # chains artifact content_hashes
    report_json: Mapped[dict] = mapped_column(JSON)  # full GapReport (cheap; audit needs it)
    framework_scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    generated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ShareLink(Base):
    """Revocable, time-limited read-only access to one snapshot."""

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_snapshots.id"), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True)  # JWT id
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class MLProposal(Base):
    """Append-only, hash-chained ML suggestion/extraction log (behind a flag).

    Every proposal is logged (model/version/prompt/raw I/O) and requires human
    confirmation to promote. Never mutates ``control_mappings``.
    """

    __tablename__ = "ml_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # suggestion|extraction
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence_artifacts.id"), index=True)
    control_id: Mapped[str | None] = mapped_column(String(64), index=True)
    proposal_json: Mapped[dict] = mapped_column(JSON)
    parent_evidence_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(64))
    prev_proposal_hash: Mapped[str | None] = mapped_column(String(64))  # hash chain
    this_proposal_hash: Mapped[str] = mapped_column(String(64), index=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
