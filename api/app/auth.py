"""Authentication primitives: PyJWT issuance/verification, password hashing, and
the FastAPI ``get_principal`` dependency (the AUTH-1 seam everything hangs off).

Tokens carry ``sub`` (user id), ``tenant_id`` (org id) and ``exp`` — never org
secrets. ``get_principal`` also sets the RLS tenant GUC on the request session so
every downstream query is automatically scoped (FOUND-2 defense-in-depth).
"""

from __future__ import annotations

import datetime as dt
import os
import secrets
import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session, set_tenant_context
from app.models_db import Membership, Organization, User

# --- password hashing --------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# --- JWT ---------------------------------------------------------------------
JWT_SECRET = os.environ.get("ACTREADY_JWT_SECRET") or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("ACTREADY_JWT_EXPIRE_MINUTES", "1440"))


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, resolved from the bearer token."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """Mint a short-lived JWT carrying sub/tenant_id/exp (no secrets)."""
    now = dt.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + dt.timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verify and decode a JWT; raise on any failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


_bearer = HTTPBearer(auto_error=True)


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Principal:
    """Resolve the caller from the bearer token and scope the session to its tenant.

    This is the AUTH-1 seam: protected routes depend on this, and it sets the
    RLS GUC so the DB enforces tenant isolation regardless of app-side filters.
    """
    claims = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(claims["sub"])
        tenant_id = uuid.UUID(claims["tenant_id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="malformed token claims",
        ) from exc

    # Confirm the membership still exists (defense against orphaned tokens).
    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user_id, Membership.org_id == tenant_id
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="principal has no membership for tenant_id",
        )

    # Scope every subsequent query on this session to the tenant (RLS).
    await set_tenant_context(session, tenant_id)
    return Principal(user_id=user_id, tenant_id=tenant_id)


# Reusable dependency type alias.
PrincipalDep = Annotated[Principal, Depends(get_principal)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def register_org_and_owner(
    session: AsyncSession,
    email: str,
    password: str,
    org_name: str,
    org_slug: str,
) -> tuple[Organization, User, Principal]:
    """Create an org + owner user + membership, return a signed Principal.

    Idempotency: a retry with the same email returns the existing identity's
    principal path. (Uniqueness on users.email / organizations.slug is enforced
    by the DB; callers should catch IntegrityError for duplicates.)
    """
    org = Organization(slug=org_slug, name=org_name)
    user = User(email=email, hashed_password=hash_password(password))
    # Scope the session to the new tenant BEFORE any write so that every insert
    # (org, user, membership) is permitted by the tenant's RLS WITH CHECK policy
    # even when the connecting role is NOBYPASSRLS (e.g. app_user in production).
    await set_tenant_context(session, org.id)
    session.add(org)
    session.add(user)
    await session.flush()  # populate ids
    session.add(Membership(org_id=org.id, user_id=user.id, role="owner"))
    await session.commit()
    principal = Principal(user_id=user.id, tenant_id=org.id)
    return org, user, principal
