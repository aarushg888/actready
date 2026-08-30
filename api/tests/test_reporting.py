"""Tests for reporting export, share links, and versioned snapshots.

Run independently of M1: tables are created via ``app.models_db.Base.metadata.
create_all`` on an in-memory SQLite engine (see conftest.py). The share/snapshot
signing uses app.auth's JWT material so it matches production exactly.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid

import pytest

from app.models import GapReport
from app.reporting import export
from app.reporting.share import (
    ShareInvalid,
    ShareRevoked,
    create_share_link,
    revoke_share,
    verify_share,
)
from app.reporting.snapshot import load_snapshot, save_snapshot

TENANT = uuid.uuid4()


# --------------------------------------------------------------------------- #
# (a) renderers produce expected substrings
# --------------------------------------------------------------------------- #
class TestRenderers:
    def test_markdown_has_score_and_status(self, report: GapReport) -> None:
        md = export.render_markdown(report)
        assert "55" in md  # readiness_score rendered
        assert "satisfied" in md
        assert "missing" in md
        assert "partial" in md
        assert "| Control |" in md  # scorecard table

    def test_json_round_trips_key_fields(self, report: GapReport) -> None:
        js = export.render_json(report)
        assert "readiness_score" in js
        assert "55" in js
        assert '"satisfied"' in js
        payload = json.loads(js)  # re-parse to ensure valid JSON
        assert payload["summary"]["total"] == 3
        assert len(payload["items"]) == 3

    def test_json_includes_evidence(self, report: GapReport, evidence) -> None:
        js = export.render_json(report, evidence=evidence)
        payload = json.loads(js)
        assert "evidence" in payload
        assert len(payload["evidence"]) == 2

    def test_html_has_score_and_per_control(self, report: GapReport) -> None:
        html_doc = export.render_html(report)
        assert "55" in html_doc
        assert "ActReady Gap Report" in html_doc
        assert "Satisfied" in html_doc
        assert "Missing" in html_doc
        for item in report.items:  # every control id present in the table
            assert item.control_id in html_doc
        assert "EUR-Lex" in html_doc  # citations footer

    def test_html_includes_evidence_links(self, report: GapReport, evidence) -> None:
        html_doc = export.render_html(report, evidence=evidence)
        assert "Evidence" in html_doc
        assert "model_card" in html_doc
        assert "policy" in html_doc


# --------------------------------------------------------------------------- #
# (b) pdf returns bytes when available, else graceful 501/fallback
# --------------------------------------------------------------------------- #
class TestPdf:
    def test_pdf_unavailable_flag(self) -> None:
        # On this host weasyprint native libs are absent -> availability is False.
        assert export.weasyprint_available() is False

    def test_render_pdf_raises_when_unavailable(self, report: GapReport) -> None:
        html_doc = export.render_html(report)
        with pytest.raises(export.WeasyUnavailable):
            export.render_pdf(html_doc)

    def test_render_pdf_returns_bytes_when_lib_present(self, report: GapReport) -> None:
        if not export._WEASYPRINT_AVAILABLE:
            pytest.skip("weasyprint not importable")
        html_doc = export.render_html(report)
        try:
            data = export.render_pdf(html_doc)
        except export.WeasyUnavailable:
            pytest.skip("weasyprint native libs missing at runtime")
        assert isinstance(data, bytes)
        assert data[:4] == b"%PDF"


# --------------------------------------------------------------------------- #
# (c) share link round-trips; rejects tampered + expired
# --------------------------------------------------------------------------- #
class TestShareLinks:
    def test_round_trip_no_db(self) -> None:
        token = create_share_link(TENANT, expires_delta=dt.timedelta(days=1))
        payload = verify_share(token)
        assert payload["tenant_id"] == str(TENANT)
        assert "jti" in payload

    def test_tampered_token_rejected(self) -> None:
        token = create_share_link(TENANT)
        with pytest.raises(ShareInvalid):
            verify_share(token + "tampered")

    def test_expired_token_rejected(self) -> None:
        token = create_share_link(TENANT, expires_delta=dt.timedelta(seconds=-1))
        with pytest.raises(ShareInvalid):
            verify_share(token)

    def test_revoked_token_rejected_in_memory(self) -> None:
        token = create_share_link(TENANT)
        revoke_share(token)
        with pytest.raises(ShareRevoked):
            verify_share(token)

    def test_revoked_token_rejected_via_db(self, db_session) -> None:
        token = create_share_link(TENANT, snapshot_id=uuid.uuid4(), db=db_session)
        revoke_share(token, db=db_session)
        with pytest.raises(ShareRevoked):
            verify_share(token, db=db_session)

    def test_round_trip_with_db_and_snapshot_id(self, db_session) -> None:
        snap_id = uuid.uuid4()
        token = create_share_link(TENANT, snapshot_id=snap_id, db=db_session)
        payload = verify_share(token, db=db_session)
        assert payload["snapshot_id"] == str(snap_id)
        assert payload["tenant_id"] == str(TENANT)

    def test_revoke_by_jti(self, db_session) -> None:
        snap_id = uuid.uuid4()
        token = create_share_link(TENANT, snapshot_id=snap_id, db=db_session)
        from app.reporting.share import _decode

        jti = _decode(token)["jti"]
        revoke_share(None, jti=jti, db=db_session)
        with pytest.raises(ShareRevoked):
            verify_share(token, db=db_session)


# --------------------------------------------------------------------------- #
# (d) snapshot save/load round-trips and pins catalog_version
# --------------------------------------------------------------------------- #
class TestSnapshots:
    def test_save_load_round_trip(self, report: GapReport, db_session) -> None:
        row = save_snapshot(
            report,
            catalog_version="eu-ai-act-2024/1689",
            manifest_hash="abc123",
            tenant_id=TENANT,
            db=db_session,
        )
        assert row.id is not None
        loaded = load_snapshot(row.id, db=db_session)
        assert loaded is not None
        assert loaded.summary["readiness_score"] == 55
        assert len(loaded.items) == 3
        assert {i.status for i in loaded.items} == {"satisfied", "partial", "missing"}

    def test_pins_catalog_version(self, report: GapReport, db_session) -> None:
        row = save_snapshot(
            report, catalog_version="OMNIBUS-2026/1744", manifest_hash="h", tenant_id=TENANT, db=db_session
        )
        assert row.catalog_version == "OMNIBUS-2026/1744"
        assert row.manifest_hash == "h"

    def test_load_missing_returns_none(self, db_session) -> None:
        assert load_snapshot(uuid.uuid4(), db=db_session) is None


# --------------------------------------------------------------------------- #
# router smoke test (import-safe, no auth dependency needed)
# --------------------------------------------------------------------------- #
class TestRouter:
    def test_report_endpoint_formats(self, report: GapReport) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.reporting.router import report_router, set_latest_report

        set_latest_report(report)
        app = FastAPI()
        app.include_router(report_router)
        client = TestClient(app)

        assert client.get("/api/report?format=json").status_code == 200
        md = client.get("/api/report?format=markdown")
        assert md.status_code == 200 and "satisfied" in md.text
        html = client.get("/api/report?format=html")
        assert html.status_code == 200 and "ActReady Gap Report" in html.text
        # pdf: graceful 501 + HTML fallback (weasyprint absent on this host)
        pdf = client.get("/api/report?format=pdf")
        assert pdf.status_code == 501
        assert "ActReady Gap Report" in pdf.text

    def test_report_endpoint_no_report_404(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.reporting.router import report_router, set_latest_report

        set_latest_report(None)  # type: ignore[arg-type]
        app = FastAPI()
        app.include_router(report_router)
        client = TestClient(app)
        assert client.get("/api/report").status_code == 404

    def test_share_endpoint_public_read(self, report: GapReport, db_session, sync_engine) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.reporting import router as router_mod
        from app.reporting.router import share_router
        from app.reporting.share import create_share_link

        # save snapshot + mint share token
        snapshot = save_snapshot(
            report, catalog_version="eu-ai-act", manifest_hash="h", tenant_id=TENANT, db=db_session
        )
        token = create_share_link(TENANT, snapshot_id=snapshot.id, db=db_session)

        router_mod.set_engine(sync_engine)  # wire get_db to the in-memory engine
        app = FastAPI()
        app.include_router(share_router)
        client = TestClient(app)

        res = client.get(f"/api/share/{token}")
        assert res.status_code == 200, res.text
        assert "ActReady Gap Report" in res.text
        assert "55" in res.text  # readiness score carried through the snapshot

        # bad token -> 401
        bad = client.get("/api/share/not-a-real-token")
        assert bad.status_code == 401

    def test_share_endpoint_revoked_410(self, report: GapReport, db_session, sync_engine) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.reporting import router as router_mod
        from app.reporting.router import share_router
        from app.reporting.share import create_share_link, revoke_share

        snapshot = save_snapshot(
            report, catalog_version="eu-ai-act", manifest_hash="h", tenant_id=TENANT, db=db_session
        )
        token = create_share_link(TENANT, snapshot_id=snapshot.id, db=db_session)
        revoke_share(token, db=db_session)

        router_mod.set_engine(sync_engine)
        app = FastAPI()
        app.include_router(share_router)
        client = TestClient(app)
        res = client.get(f"/api/share/{token}")
        assert res.status_code == 410
