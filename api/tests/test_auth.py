"""Auth tests: signup + login return a usable JWT (AUTH-1 / AUTH-2)."""

from __future__ import annotations

import jwt

from app.auth import JWT_ALGORITHM, JWT_SECRET


async def test_register_returns_jwt(client):
    resp = await client.post(
        "/auth/register",
        json={
            "email": "owner@acme.com",
            "password": "supersecret1",
            "org_name": "Acme Inc",
            "org_slug": "acme-inc",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    # Token carries sub + tenant_id + exp, no secrets.
    claims = jwt.decode(body["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert "sub" in claims and "tenant_id" in claims and "exp" in claims


async def test_register_then_login(client):
    await client.post(
        "/auth/register",
        json={
            "email": "login@acme.com",
            "password": "supersecret1",
            "org_name": "Acme Inc",
            "org_slug": "acme-login",
        },
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "login@acme.com", "password": "supersecret1"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


async def test_login_wrong_password_rejected(client):
    await client.post(
        "/auth/register",
        json={
            "email": "bad@acme.com",
            "password": "supersecret1",
            "org_name": "Acme Inc",
            "org_slug": "acme-bad",
        },
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "bad@acme.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_register_duplicate_email_conflict(client):
    payload = {
        "email": "dup@acme.com",
        "password": "supersecret1",
        "org_name": "Acme Inc",
        "org_slug": "acme-dup",
    }
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 200
    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


async def test_protected_route_requires_token(client):
    resp = await client.post("/api/assess")
    assert resp.status_code == 401


async def test_protected_route_accepts_valid_token(client):
    reg = await client.post(
        "/auth/register",
        json={
            "email": "prot@acme.com",
            "password": "supersecret1",
            "org_name": "Acme Inc",
            "org_slug": "acme-prot",
        },
    )
    token = reg.json()["access_token"]
    resp = await client.post(
        "/api/assess",
        headers={"Authorization": f"Bearer {token}"},
    )
    # 200 with a report (org has no evidence yet -> all missing, deterministic).
    assert resp.status_code == 200, resp.text
    assert "summary" in resp.json()
