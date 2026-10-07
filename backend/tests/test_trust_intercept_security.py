"""Security regression tests for TRUST//INTERCEPT.

Covers the four audit areas:
1. Structural HITL control — no `action_taken` outside /case/{id}/decision.
2. PII protection — originals never persisted, corrections redacted.
3. Graceful fallbacks — WHOIS/VirusTotal/LLM failures never raise 500s.
4. CORS — preflight from http://127.0.0.1:5173 is accepted.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import types

# Configure BEFORE importing the app (settings are cached).
_TEST_DB = os.path.join(tempfile.gettempdir(), "trust-intercept_security_test.db")
os.environ.update(
    {
        "DB_PATH": _TEST_DB,
        "LLM_PROVIDER": "none",  # force deterministic template mode
        "ALLOW_OUTBOUND_LOOKUPS": "false",  # no network in CI
    }
)
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.tools import domain_lookup  # noqa: E402

SCAM = (
    "SINGPOST: Your parcel is held at our depot due to an unpaid delivery fee of $1.99. "
    "Settle within 24 hours. Confirm at https://bit.ly/parcel-hold-9x2 — enter your IC number "
    "S1234567D, card 4111 1111 1111 1111 and OTP. Urgent! Call +65 9123 4567."
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def scam_case_id(client):
    response = client.post("/case", json={"input_type": "text", "text": SCAM})
    assert response.status_code == 200, response.text
    return response.json()["case"]["id"]


# ---------------------------------------------------------------------------
# 1. Structural HITL control
# ---------------------------------------------------------------------------


def test_verdict_has_no_action_taken_field(client, scam_case_id):
    view = client.get(f"/case/{scam_case_id}").json()
    verdict = view["verdict"]
    assert "action_taken" not in verdict
    assert verdict["action_required"] is True
    assert view["decisions"] == []  # nothing has happened without approval


def test_action_taken_only_written_via_decision_endpoint(client, scam_case_id):
    before = client.get(f"/case/{scam_case_id}").json()
    assert before["decisions"] == []

    response = client.post(
        f"/case/{scam_case_id}/decision",
        json={"human_action": "report", "decided_by": "auditor"},
    )
    assert response.status_code == 200
    after = response.json()

    assert len(after["decisions"]) == 1
    decision = after["decisions"][0]
    assert decision["action_taken"]  # only a Decision carries this field
    assert "verdict_snapshot" in decision and decision["verdict_snapshot"]["score"]
    assert "action_taken" not in after["verdict"]  # still absent from the Verdict


def test_invalid_action_rejected(client, scam_case_id):
    response = client.post(
        f"/case/{scam_case_id}/decision",
        json={"human_action": "nuke_everything"},
    )
    assert response.status_code == 422  # enum validation — no side channel


def test_disagree_requires_correction(client, scam_case_id):
    response = client.post(
        f"/case/{scam_case_id}/decision",
        json={"human_action": "disagree_recheck", "correction": "   "},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 2. PII protection
# ---------------------------------------------------------------------------


def test_originals_never_persisted(scam_case_id):
    conn = sqlite3.connect(_TEST_DB)
    try:
        rows = conn.execute("SELECT redacted_text FROM cases").fetchall()
        payloads = conn.execute("SELECT payload FROM verdicts").fetchall()
        decisions = conn.execute("SELECT payload FROM decisions").fetchall()
        evidence = conn.execute("SELECT raw_output FROM evidence").fetchall()
    finally:
        conn.close()

    secrets = ["S1234567D", "4111 1111 1111 1111", "9123 4567"]
    blob = json.dumps(
        [r[0] for r in rows]
        + [p[0] for p in payloads]
        + [d[0] for d in decisions]
        + [e[0] for e in evidence]
    )
    for secret in secrets:
        assert secret not in blob, f"PII leaked into the database: {secret}"
    assert "[REDACTED_IC_NRIC_1]" in rows[0][0]


def test_user_correction_is_redacted(client, scam_case_id):
    response = client.post(
        f"/case/{scam_case_id}/decision",
        json={
            "human_action": "disagree_recheck",
            "correction": "This is my real courier, my IC is G1234567J, call 98765432.",
        },
    )
    assert response.status_code == 200
    decision = response.json()["decisions"][-1]
    assert "G1234567J" not in decision["correction"]
    assert "[REDACTED" in decision["correction"]
    case_text = response.json()["case"]["redacted_text"]
    assert "G1234567J" not in case_text
    assert "[User correction]" in case_text


def test_redaction_is_idempotent():
    from backend.tools.pii_redact import redact_pii

    once, findings = redact_pii("IC S1234567D and 4111 1111 1111 1111")
    twice, findings2 = redact_pii(once)
    assert twice == once  # placeholders are never double-wrapped
    assert findings2 == []


def test_otp_codes_are_redacted():
    from backend.tools.pii_redact import redact_pii

    text = (
        "Your account is locked. Enter OTP 884213 within 5 minutes, "
        "or call the driver at +65 9123 4567."
    )
    redacted, findings = redact_pii(text, use_ner=False)

    assert "884213" not in redacted                        # the code itself is gone
    assert "[REDACTED_OTP_1]" in redacted                  # placeholder present
    assert "OTP" in redacted  # keyword kept → downstream credential cues still fire
    assert any(f.entity_type == "OTP" for f in findings)   # finding recorded for audit

    # Reversed phrasing: "884213 is your Singpass OTP".
    reversed_redacted, reversed_findings = redact_pii("884213 is your Singpass OTP", use_ner=False)
    assert "884213" not in reversed_redacted
    assert any(f.entity_type == "OTP" for f in reversed_findings)

    # Phone numbers are NOT mistaken for OTPs (long digit run + no keyword).
    phone_redacted, phone_findings = redact_pii("Call +65 9123 4567 now", use_ner=False)
    assert not any(f.entity_type == "OTP" for f in phone_findings)


# ---------------------------------------------------------------------------
# 3. Graceful fallbacks (no 500s when external APIs die)
# ---------------------------------------------------------------------------


def test_domain_lookup_survives_network_timeouts(monkeypatch):
    domain_lookup.clear_cache()

    def boom(*args, **kwargs):
        raise httpx.ConnectTimeout("simulated network timeout")

    monkeypatch.setattr(
        domain_lookup,
        "get_settings",
        lambda: types.SimpleNamespace(
            allow_outbound_lookups=True,
            virustotal_api_key="test-key",
            safe_browsing_api_key="test-key",
            outbound_timeout_seconds=0.1,
            reputation_cache_ttl_seconds=1,
        ),
    )
    monkeypatch.setattr(domain_lookup, "_add_whois_age", lambda intel: None)
    monkeypatch.setattr(domain_lookup.httpx, "get", boom)
    monkeypatch.setattr(domain_lookup.httpx, "post", boom)

    intel = domain_lookup.lookup_domain("https://example.com/track")
    assert intel.domain == "example.com"
    for rep in intel.reputation:
        assert rep.checked is False
        assert "timeout" in rep.unavailable_reason.lower()
    assert intel.domain_age_days is None
    assert any("age" in note.lower() for note in intel.notes)


def test_offline_mode_never_500s(client):
    # ALLOW_OUTBOUND_LOOKUPS=false is the full-offline demo mode.
    response = client.post(
        "/case",
        json={"input_type": "text", "text": "Check this link please https://example.com/track/1"},
    )
    assert response.status_code == 200
    view = response.json()
    assert view["verdict"]["confidence"] in ("low", "medium", "high")
    link_entries = [e for e in view["evidence"] if e["tool"] == "module_2_link_safety"]
    assert link_entries and "error" in json.dumps(link_entries[0]["raw_output"]).lower()


def test_llm_template_mode_produces_complete_verdict(client, scam_case_id):
    view = client.get(f"/case/{scam_case_id}").json()
    verdict = view["verdict"]
    assert verdict["score"] in ("low", "medium", "high")
    assert verdict["confidence"] in ("low", "medium", "high")
    assert verdict["cues"], "rule-based cues must exist even without an LLM"
    assert verdict["reasoning_trace"]["llm_used"] is False


# ---------------------------------------------------------------------------
# 4. CORS: frontend (127.0.0.1:5173) <-> backend (127.0.0.1:8000) match
# ---------------------------------------------------------------------------


def test_cors_preflight_from_react_dev_server(client):
    response = client.options(
        "/case",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_health_endpoint_configuration(client):
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["outbound_lookups_enabled"] is False
    assert health["llm"]["template_mode"] is True
