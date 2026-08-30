"""GitHub App integration adapter (INT-1).

Provides:
  * ``mint_installation_token``  - short-lived installation token via a JWT app
                                    assertion (uses APP_ID + PRIVATE_KEY env; a fake
                                    callable can be injected for tests).
  * ``verify_webhook``           - HMAC-SHA256 (X-Hub-Signature-256) verification of
                                    inbound webhooks.
  * ``GitHubSource``            - an EvidenceSource that lists repo contents for
                                    model_card / policy / eval files and returns
                                    RawEvidence items. Fully testable with an
                                    httpx MockTransport (no real network).

The adapter uses ``httpx`` directly (no extra GitHub client lib per the plan).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import time
from collections.abc import Callable

import httpx
import jwt

from app.integrations.types import RawEvidence

# Files the adapter looks for in each configured repo.
_MODEL_CARD_PATHS = ("model_card.yaml", "model_card.yml")
_POLICY_PATHS = ("docs/ai-policy.md", "AI_POLICY.md", "policy.md")
_EVAL_PATHS = ("eval_results.json", ".github/eval_results.json")


def _now() -> int:
    return int(time.time())


def mint_installation_token(
    installation_id: str | int,
    *,
    app_id: str | None = None,
    private_key: str | None = None,
    jwt_factory: Callable[[str, str], str] | None = None,
    http_client: httpx.Client | None = None,
) -> str:
    """Mint a short-lived GitHub App installation token.

    In production this reads ``APP_ID`` / ``PRIVATE_KEY`` from the environment.
    For tests, pass ``jwt_factory`` (returns a bearer JWT) and/or ``http_client``
    (an ``httpx.Client`` with a ``MockTransport``).
    """
    app_id = app_id or _env("APP_ID")
    private_key = private_key or _env("PRIVATE_KEY")

    def _default_jwt(a_id: str, a_key: str) -> str:
        now = _now()
        payload = {
            "iat": now - 60,
            "exp": now + 540,  # GitHub caps app JWT at 10 minutes
            "iss": a_id,
        }
        return jwt.encode(payload, a_key, algorithm="RS256")

    if jwt_factory is not None:
        # Test/headless path: caller supplies the JWT minting callable, so real
        # app credentials are not required.
        app_jwt = jwt_factory(app_id or "", private_key or "")
    else:
        if app_id is None or private_key is None:
            raise RuntimeError(
                "GitHub App credentials missing: set APP_ID and PRIVATE_KEY "
                "(or inject jwt_factory for tests)"
            )
        app_jwt = _default_jwt(app_id, private_key)

    client = http_client or httpx.Client()
    try:
        resp = client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]
    finally:
        if http_client is None:
            client.close()


def verify_webhook(
    payload: bytes | str,
    signature: str,
    secret: str,
) -> bool:
    """Verify a GitHub webhook HMAC-SHA256 signature (X-Hub-Signature-256).

    ``signature`` is the raw header value, e.g. ``sha256=abc123...``.
    Returns True only when the HMAC matches. Uses constant-time comparison.
    """
    if not signature or "=" not in signature:
        return False
    algorithm, _, expected = signature.partition("=")
    if algorithm != "sha256":
        return False
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)


class GitHubSource:
    """EvidenceSource that pulls model_card / policy / eval files from GitHub repos."""

    name = "github_app"

    def __init__(
        self,
        installation_id: str | int,
        repos: list[str],
        *,
        token: str | None = None,
        token_factory: Callable[[], str] | None = None,
        http_client: httpx.Client | None = None,
        app_id: str | None = None,
        private_key: str | None = None,
        jwt_factory: Callable[[str, str], str] | None = None,
    ) -> None:
        self.installation_id = installation_id
        self.repos = repos
        self._token = token
        self._token_factory = token_factory
        self._http_client = http_client
        self._app_id = app_id
        self._private_key = private_key
        self._jwt_factory = jwt_factory

    # -- EvidenceSource protocol ------------------------------------------
    def fetch(self) -> list[RawEvidence]:
        token = self._resolve_token()
        client = self._http_client or httpx.Client(
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json"}
        )
        try:
            out: list[RawEvidence] = []
            for repo in self.repos:
                # model card
                for path in _MODEL_CARD_PATHS:
                    content = self._get_file(client, repo, path)
                    if content is not None:
                        out.append(
                            RawEvidence(
                                evidence_type="model_card",
                                content={"text": content.decode("utf-8", "replace")},
                                collected_at=dt.date.today(),
                                source_name=f"github:{repo}:{path}",
                            )
                        )
                        break
                # policy doc
                for path in _POLICY_PATHS:
                    content = self._get_file(client, repo, path)
                    if content is not None:
                        out.append(
                            RawEvidence(
                                evidence_type="policy",
                                content={"text": content.decode("utf-8", "replace")},
                                collected_at=dt.date.today(),
                                source_name=f"github:{repo}:{path}",
                            )
                        )
                        break
                # eval run artifact
                for path in _EVAL_PATHS:
                    content = self._get_file(client, repo, path)
                    if content is not None:
                        out.append(
                            RawEvidence(
                                evidence_type="eval_run",
                                content={"raw": content.decode("utf-8", "replace")},
                                collected_at=dt.date.today(),
                                source_name=f"github:{repo}:{path}",
                            )
                        )
                        break
            return out
        finally:
            if self._http_client is None:
                client.close()

    # -- internals --------------------------------------------------------
    def _resolve_token(self) -> str:
        if self._token:
            return self._token
        if self._token_factory:
            return self._token_factory()
        return mint_installation_token(
            self.installation_id,
            app_id=self._app_id,
            private_key=self._private_key,
            jwt_factory=self._jwt_factory,
            http_client=self._http_client,
        )

    def _get_file(self, client: httpx.Client, repo: str, path: str) -> bytes | None:
        resp = client.get(f"https://api.github.com/repos/{repo}/contents/{path}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content


def _env(name: str) -> str | None:
    import os

    return os.environ.get(name)
