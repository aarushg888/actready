"""Auth routes: POST /auth/register and POST /auth/login.

Register creates an Organization + owner User + Membership (AUTH-2) and returns a
JWT. Login verifies credentials and returns a JWT. Both tokens carry ``sub`` and
``tenant_id`` and are consumable by the ``get_principal`` dependency.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth import (
    SessionDep,
    create_access_token,
    register_org_and_owner,
    verify_password,
)
from app.models_db import User

router = APIRouter(prefix="/auth", tags=["auth"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    org_name: str = Field(min_length=1, max_length=255)
    org_slug: str = Field(min_length=2, max_length=64)

    def validate_slug(self) -> None:
        if not _SLUG_RE.match(self.org_slug):
            raise ValueError(
                "org_slug must be 2-64 chars: lowercase letters, digits, hyphens; "
                "must start with a letter or digit"
            )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def register(body: RegisterRequest, session: SessionDep) -> TokenResponse:
    try:
        body.validate_slug()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        _org, _user, principal = await register_org_and_owner(
            session,
            email=str(body.email),
            password=body.password,
            org_name=body.org_name,
            org_slug=body.org_slug,
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email or org_slug already registered",
        ) from None

    token = create_access_token(principal.user_id, principal.tenant_id)
    return TokenResponse(
        access_token=token,
        tenant_id=str(principal.tenant_id),
        user_id=str(principal.user_id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == str(body.email)))
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        )
    # Use the user's first membership as the active tenant for the issued token.
    from app.models_db import Membership

    mem = await session.scalar(
        select(Membership).where(Membership.user_id == user.id).order_by(Membership.role)
    )
    if mem is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user has no organization membership",
        )
    token = create_access_token(user.id, mem.org_id)
    return TokenResponse(
        access_token=token,
        tenant_id=str(mem.org_id),
        user_id=str(user.id),
    )
