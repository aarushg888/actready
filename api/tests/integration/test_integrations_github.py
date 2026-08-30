"""Tests: GitHub App adapter (INT-1) - HMAC webhook verification + fetch.

(b) verify_webhook accepts good sig, rejects tampered/bad sig.
    Also exercises fetch() over an httpx MockTransport (no real network).
"""

from __future__ import annotations

import httpx
import pytest

from app.integrations import github
from app.integrations.types import RawEvidence

SECRET = "super-secret-webhook-secret"


def _sign(payload: bytes, secret: str = SECRET) -> str:
    import hashlib
    import hmac

    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestWebhookVerification:
    def test_accepts_good_signature(self) -> None:
        payload = b'{"action":"push","repo":"acme/model"}'
        sig = _sign(payload)
        assert github.verify_webhook(payload, sig, SECRET) is True

    def test_rejects_tampered_payload(self) -> None:
        payload = b'{"action":"push","repo":"acme/model"}'
        sig = _sign(payload)
        assert github.verify_webhook(payload + b"tampered", sig, SECRET) is False

    def test_rejects_wrong_secret(self) -> None:
        payload = b'{"action":"push"}'
        sig = _sign(payload, secret="other-secret")
        assert github.verify_webhook(payload, sig, SECRET) is False

    def test_rejects_malformed_signature(self) -> None:
        payload = b"{}"
        assert github.verify_webhook(payload, "not-a-sig", SECRET) is False

    def test_rejects_empty_signature(self) -> None:
        assert github.verify_webhook(b"{}", "", SECRET) is False

    def test_rejects_non_sha256_algorithm(self) -> None:
        payload = b"{}"
        digest = _sign(payload)
        bad = "sha1=" + digest.split("=", 1)[1]
        assert github.verify_webhook(payload, bad, SECRET) is False


class TestGitHubSourceFetch:
    def _transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            # contents endpoint for the configured repo
            if request.url.path.endswith("/contents/model_card.yaml"):
                return httpx.Response(200, content=b"model_name: demo\nowner: acme\n")
            if request.url.path.endswith("/contents/docs/ai-policy.md"):
                return httpx.Response(200, content=b"# AI Policy\n")
            if request.url.path.endswith("/contents/eval_results.json"):
                return httpx.Response(200, content=b'{"results":[]}')
            return httpx.Response(404)

        return httpx.MockTransport(handler)

    def test_fetch_returns_model_card_policy_eval(self) -> None:
        client = httpx.Client(transport=self._transport())
        src = github.GitHubSource("123", ["acme/demo"], token="tok", http_client=client)
        ev = src.fetch()
        types = {e.evidence_type for e in ev}
        assert "model_card" in types
        assert "policy" in types
        assert "eval_run" in types
        for e in ev:
            assert isinstance(e, RawEvidence)

    def test_fetch_handles_missing_files_gracefully(self) -> None:
        transport = httpx.MockTransport(lambda req: httpx.Response(404))
        client = httpx.Client(transport=transport)
        src = github.GitHubSource("123", ["acme/empty"], token="tok", http_client=client)
        assert src.fetch() == []

    def test_fetch_propagates_http_errors(self) -> None:
        transport = httpx.MockTransport(lambda req: httpx.Response(500))
        client = httpx.Client(transport=transport)
        src = github.GitHubSource("123", ["acme/boom"], token="tok", http_client=client)
        with pytest.raises(Exception):
            src.fetch()


class TestInstallationToken:
    def test_missing_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APP_ID", raising=False)
        monkeypatch.delenv("PRIVATE_KEY", raising=False)
        with pytest.raises(RuntimeError):
            github.mint_installation_token("123")

    def test_jwt_factory_injected_no_network(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APP_ID", raising=False)
        monkeypatch.delenv("PRIVATE_KEY", raising=False)

        calls: dict[str, int] = {}

        def fake_jwt(app_id: str, private_key: str) -> str:
            calls["jwt"] = 1
            return "fake.jwt.token"

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer fake.jwt.token"
            return httpx.Response(201, json={"token": "inst-token-xyz"})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        token = github.mint_installation_token(
            "123", jwt_factory=fake_jwt, http_client=client
        )
        assert token == "inst-token-xyz"
        assert calls.get("jwt") == 1
