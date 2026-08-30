"""Signed, revocable share links for read-only public report access.

A share link is a JWT carrying a ``jti`` (random id) that maps 1:1 to a
``ShareLink`` row in ``app.models_db``. Revocation is two-tier:
  * a fast in-memory set (``_REVOKED``) for process-local immediate invalidation, and
  * the persisted ``share_links.revoked`` flag in Postgres (M1's source of truth).

Signing uses ``app.auth`` JWT helpers/secret when a share helper exists there;
otherwise this module signs locally with ``app.auth.JWT_SECRET`` (HS256). The
token authorises access to the single snapshot it was minted for — no tenant
credentials required (GET /api/share/{token}).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import jwt
from sqlalchemy import select

# M1 only ships generic JWT access tokens today (no share-specific sign/verify
# helpers), so we sign locally with the app JWT secret. We deliberately import
# only symbols that exist in app.auth; the M1 share helpers are referenced behind
# a try/except at runtime and typed as None here so mypy does not flag them.
from app.auth import JWT_ALGORITHM, JWT_SECRET  # noqa: E402
from app.models_db import Base, ShareLink

try:  # pragma: no cover - branch depends on M1 landing a share helper
    # Imported lazily/typed so the (currently absent) M1 helpers don't break mypy.
    from app.auth import sign_share_token as _m1_sign  # type: ignore[attr-defined]
    from app.auth import verify_share_token as _m1_verify  # type: ignore[attr-defined]

    _USING_M1_AUTH = True
except Exception:  # M1 only ships generic JWT access tokens today
    _m1_sign = _m1_verify = None
    _USING_M1_AUTH = False

SHARE_ALGORITHM = JWT_ALGORITHM if _USING_M1_AUTH else "HS256"
SHARE_SECRET = None if _USING_M1_AUTH else JWT_SECRET
_DEFAULT_TTL = dt.timedelta(days=7)

# Process-local revocation fast-set (mirrors the DB `revoked` flag for speed).
_REVOKED: set[str] = set()


class ShareError(Exception):
    """Base class for share-link failures."""


class ShareInvalid(ShareError):
    """Token is malformed, expired, or fails signature verification."""


class ShareRevoked(ShareError):
    """Token has been explicitly revoked."""


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def create_share_link(
    tenant_id: object,
    expires_delta: dt.timedelta | None = None,
    snapshot_id: object | None = None,
    *,
    db: Any | None = None,
) -> str:
    """Mint a signed, revocable share token for ``tenant_id`` / ``snapshot_id``.

    If ``db`` (a SQLAlchemy Session) is supplied, a revocable ``ShareLink`` row is
    persisted (jti + expiry + snapshot_id). Without a DB, the token is still valid
    for signature/expiry checks but cannot be revoked via the registry.
    """
    expires_delta = expires_delta or _DEFAULT_TTL
    jti = uuid.uuid4().hex
    expires_at = _utcnow() + expires_delta

    if _USING_M1_AUTH:
        token = _m1_sign(  # type: ignore[union-attr]
            tenant_id=tenant_id, jti=jti, exp=expires_at, snapshot_id=snapshot_id
        )
    else:
        payload = {
            "tenant_id": str(tenant_id),
            "jti": jti,
            "snapshot_id": str(snapshot_id) if snapshot_id is not None else None,
            "exp": int(expires_at.timestamp()),
            "iat": int(_utcnow().timestamp()),
            "type": "share",
        }
        token = jwt.encode(payload, SHARE_SECRET, algorithm=SHARE_ALGORITHM)  # type: ignore[arg-type]

    if db is not None:
        db.add(
            ShareLink(
                jti=jti,
                snapshot_id=snapshot_id,
                expires_at=expires_at,
                revoked=False,
            )
        )
        db.commit()

    return token


def _decode(token: str) -> dict[str, Any]:
    try:
        if _USING_M1_AUTH:
            return _m1_verify(token)  # type: ignore[union-attr]
        return jwt.decode(token, SHARE_SECRET, algorithms=[SHARE_ALGORITHM])  # type: ignore[arg-type]
    except jwt.ExpiredSignatureError as exc:
        raise ShareInvalid("share link expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ShareInvalid(f"invalid share token: {exc}") from exc


def verify_share(token: str, *, db: Any | None = None) -> dict[str, Any]:
    """Verify a share token; returns its payload or raises ``ShareError``.

    Order: signature/expiry → in-memory revocation set → persisted ``revoked``
    flag (when ``db`` supplied) → persisted expiry (authoritative).
    """
    payload = _decode(token)
    jti = payload.get("jti")
    if jti is not None and jti in _REVOKED:
        raise ShareRevoked("share link has been revoked")

    if db is not None and jti is not None:
        row = db.scalar(select(ShareLink).where(ShareLink.jti == jti))
        if row is None:
            raise ShareInvalid("unknown share link")
        if row.revoked:
            _REVOKED.add(jti)
            raise ShareRevoked("share link has been revoked")
        if row.expires_at is not None:
            exp = row.expires_at
            if exp.tzinfo is None:  # SQLite stores naive; make tz-aware for compare
                exp = exp.replace(tzinfo=dt.UTC)
            if exp <= _utcnow():
                raise ShareInvalid("share link expired")
    return payload


def revoke_share(token: str | None = None, *, jti: str | None = None, db: Any | None = None) -> None:
    """Revoke a share link by token or by jti (immediate + persisted if db given)."""
    if jti is None and token is not None:
        try:
            jti = _decode(token).get("jti")
        except ShareError:
            jti = None
    if not jti:
        raise ShareInvalid("cannot revoke: no jti")
    _REVOKED.add(jti)
    if db is not None:
        row = db.scalar(select(ShareLink).where(ShareLink.jti == jti))
        if row is not None:
            row.revoked = True
            db.commit()


def create_tables(engine: Any) -> None:
    """Create reporting tables from M1's Base (used by tests + bootstrap)."""
    Base.metadata.create_all(engine)


def drop_tables(engine: Any) -> None:
    """Drop reporting tables (used by tests)."""
    Base.metadata.drop_all(engine)


__all__ = [
    "ShareError",
    "ShareInvalid",
    "ShareRevoked",
    "create_share_link",
    "verify_share",
    "revoke_share",
    "create_tables",
    "drop_tables",
    "_REVOKED",
]
