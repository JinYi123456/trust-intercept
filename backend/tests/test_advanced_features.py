"""Regression tests for the advanced features:

* Multi-Agent Debate Protocol (Red/Blue transcript logged, resolution policy)
* Audio forensics intake (local DSP pass on PCM WAV, graceful degradation)
* Federated Scam Intelligence Network (hash validation, report flow, stats)

NOTE: this file may be imported BEFORE test_trust-intercept_security.py (alphabetical
collection), so it must apply the SAME env configuration (isolated temp DB,
LLM off, no outbound calls) BEFORE importing the app — settings are cached on
first import, and whichever module imports first decides the config for the
whole session. Sharing the security suite's temp-DB path keeps every test
module on one consistent, disposable database.
"""
from __future__ import annotations

import os
import tempfile

_TEST_DB = os.path.join(tempfile.gettempdir(), "trust-intercept_security_test.db")
os.environ.update(
    {
        "DB_PATH": _TEST_DB,
        "LLM_PROVIDER": "none",  # force deterministic template mode + offline debate
        "ALLOW_OUTBOUND_LOOKUPS": "false",  # no network in CI
    }
)

import base64  # noqa: E402
import io  # noqa: E402
import math  # noqa: E402
import struct  # noqa: E402
import wave  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

SCAM_TEXT = (
    "SINGPOST: Your parcel is HELD at our depot due to an unpaid delivery fee of $1.99. "
    "Settle within 24 hours: https://bit.ly/parcel-hold-9x2 — enter your IC number "
    "S1234567D, card 4111 1111 1111 1111 and the OTP. Urgent!"
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _make_wav(seconds: float = 3.0, rate: int = 16000) -> bytes:
    """A 220 Hz sine tone — realistic enough to exercise the DSP metrics."""
    frames = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate)))
        for i in range(int(rate * seconds))
    )
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Task 1 — Multi-Agent Debate Protocol
# ---------------------------------------------------------------------------


def test_debate_transcript_logged_with_two_rounds(client):
    response = client.post("/case", json={"input_type": "text", "text": SCAM_TEXT})
    assert response.status_code == 200
    body = response.json()

    debates = [entry for entry in body["evidence"] if entry["tool"] == "agent_debate"]
    assert debates, "the Red/Blue debate must be stored in the case evidence"

    transcript = debates[-1]["raw_output"]
    assert len(transcript["rounds"]) == 2
    assert transcript["agents"]["red"]["position"] == "scam"
    assert transcript["agents"]["blue"]["position"] == "legitimate"

    resolution = transcript["resolution"]
    assert resolution["red_vote"] in ("low", "medium", "high")
    assert resolution["blue_vote"] in ("low", "medium", "high")
    assert "may never lower" in resolution["policy"]
    assert resolution["consensus"] in (
        "unanimous_scam", "unanimous_safe", "leaning_scam", "leaning_safe", "contested"
    )


def test_debate_raises_but_never_lowers_rule_floor(client):
    response = client.post("/case", json={"input_type": "text", "text": SCAM_TEXT})
    body = response.json()
    verdict = body["verdict"]

    # The scam case must stay HIGH regardless of the debate outcome — the
    # debate may raise the risk above the rule floor, never lower it.
    assert verdict["score"] == "high"

    reasoning = verdict["reasoning_trace"]
    assert reasoning["debate"]["transcript_evidence_tool"] == "agent_debate"
    assert reasoning["debate"]["rounds"] >= 1
    assert reasoning["debate"]["consensus"] in (
        "unanimous_scam", "unanimous_safe", "leaning_scam", "leaning_safe", "contested"
    )


def test_legit_case_not_inflated_by_debate(client):
    response = client.post(
        "/case",
        json={
            "input_type": "text",
            "text": (
                "DHL Express: Your shipment D-9823 is out for delivery today between 2pm and "
                "6pm. Track it at https://www.dhl.com/track. No action needed if you are home."
            ),
        },
    )
    body = response.json()
    verdict = body["verdict"]

    # Blue's default vote must not raise a clean case — the prosecution-only
    # raise policy keeps the false-positive safeguard intact.
    assert verdict["score"] == "low"


# ---------------------------------------------------------------------------
# Task 2 — Audio forensics
# ---------------------------------------------------------------------------


def test_audio_case_runs_local_pass_and_returns_findings(client):
    audio_b64 = base64.b64encode(_make_wav()).decode()
    response = client.post(
        "/case",
        json={
            "input_type": "audio",
            "audio_b64": audio_b64,
            "audio_filename": "voicemail.wav",
            "text": "Pay the transfer now, do not call anyone",
        },
    )
    assert response.status_code == 200
    body = response.json()

    audio_entries = [entry for entry in body["evidence"] if entry["tool"] == "audio_forensics"]
    assert audio_entries, "audio cases must log an audio_forensics evidence entry"
    payload = audio_entries[-1]["raw_output"]

    assert payload["local_pass"]["decoded"] is True
    assert payload["local_pass"]["sample_rate"] == 16000
    assert payload["duration_seconds"] == pytest.approx(3.0, abs=0.1)
    # The context text carries coercion language -> at least one transcript finding.
    cue_types = {finding["cue_type"] for finding in payload["findings"]}
    assert "urgent_wire_transfer" in cue_types or "isolation_instruction" in cue_types

    # The verdict must incorporate the audio module (medium via coercion raise).
    assert body["verdict"]["score"] in ("low", "medium", "high")
    assert body["verdict"]["action_required"] is True


def test_audio_without_file_rejected(client):
    response = client.post("/case", json={"input_type": "audio", "audio_b64": ""})
    assert response.status_code == 400


def test_audio_oversize_rejected(client):
    big = base64.b64encode(b"\0" * (21 * 1024 * 1024)).decode()
    response = client.post(
        "/case",
        json={"input_type": "audio", "audio_b64": big, "audio_filename": "huge.wav"},
    )
    assert response.status_code == 413


def test_audio_invalid_base64_rejected(client):
    response = client.post(
        "/case",
        json={"input_type": "audio", "audio_b64": "not-base64!!!", "audio_filename": "x.wav"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Task 3 — Federated Scam Intelligence Network
# ---------------------------------------------------------------------------


def test_report_hash_validation(client):
    # Invalid hash rejected.
    response = client.post(
        "/community/report-hash",
        json={"hash": "nothex", "kind": "url"},
    )
    assert response.status_code == 422

    # Invalid kind rejected.
    response = client.post(
        "/community/report-hash",
        json={"hash": "a" * 64, "kind": "phone"},
    )
    assert response.status_code == 422

    # Valid hash accepted.
    response = client.post(
        "/community/report-hash",
        json={"hash": "b" * 64, "kind": "url", "risk": "high", "source": "ui_report"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in ("recorded", "known")
    assert payload["network"]["nodes_synced"] >= 1


def test_report_hash_dedup_counts_reports(client):
    digest = "c" * 64
    first = client.post("/community/report-hash", json={"hash": digest, "kind": "url"})
    second = client.post("/community/report-hash", json={"hash": digest, "kind": "url"})
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == "recorded"
    assert second.json()["status"] == "known"
    assert second.json()["report_count"] >= 2


def test_community_stats_endpoint(client):
    response = client.get("/community/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["nodes_synced"] >= 1
    assert "indicators" in stats and "report_events" in stats
    assert "SHA-256" in stats["privacy_note"]


def test_report_decision_shares_indicator_hashes(client):
    # Submit a scam case with a URL, then approve a report — the community
    # intel store must record the anonymous indicator hashes.
    created = client.post("/case", json={"input_type": "text", "text": SCAM_TEXT})
    case_id = created.json()["case"]["id"]

    decided = client.post(
        f"/case/{case_id}/decision",
        json={"human_action": "report", "correction": "", "decided_by": "pytest"},
    )
    assert decided.status_code == 200

    intel = [
        entry
        for entry in decided.json()["evidence"]
        if entry["tool"] == "community_intel"
    ]
    assert intel, "the report flow must log a community_intel evidence entry"
    assert intel[-1]["raw_output"]["action"] == "threat_indicator_hashes_shared"
    assert "SHA-256 hashes only" in intel[-1]["raw_output"]["privacy"]

    stats = client.get("/community/stats").json()
    assert stats["indicators"] >= 1


# ---------------------------------------------------------------------------
# Task 3b/3c — Psychological Manipulation Radar + Honeypot Sandbox Recon
# ---------------------------------------------------------------------------


def test_psych_radar_logged_with_vectors_and_barrier(client):
    response = client.post("/case", json={"input_type": "text", "text": SCAM_TEXT})
    assert response.status_code == 200
    body = response.json()

    radars = [entry for entry in body["evidence"] if entry["tool"] == "psych_radar"]
    assert radars, "the manipulation radar must be logged as evidence"
    radar = radars[-1]["raw_output"]

    names = {vector["name"] for vector in radar["vectors"]}
    assert "Urgency Pressure" in names
    assert "Credential Harvesting" in names  # IC/card/OTP requests
    assert "Deceptive Framing" in names  # bit.ly shortener
    assert 0 < radar["overall"] <= 1
    assert radar["cooling_off_required"] is True
    # Deterministic: every vector carries its quoted evidence basis.
    for vector in radar["vectors"]:
        assert vector["basis"], "vectors must disclose the cue that fired"


def test_radar_clean_case_needs_no_barrier(client):
    response = client.post(
        "/case",
        json={
            "input_type": "text",
            "text": (
                "DHL Express: Your shipment D-9823 is out for delivery today between 2pm and "
                "6pm. Track it at https://www.dhl.com/track. No action needed if you are home."
            ),
        },
    )
    body = response.json()
    radars = [entry for entry in body["evidence"] if entry["tool"] == "psych_radar"]
    assert radars, "radar evidence is logged for every case"
    radar = radars[-1]["raw_output"]
    assert radar["cooling_off_required"] is False
    assert radar["overall"] == 0


def test_sandbox_recon_refused_for_low_risk(client):
    created = client.post(
        "/case",
        json={
            "input_type": "text",
            "text": (
                "DHL Express: Your shipment D-9823 is out for delivery today. Track it at "
                "https://www.dhl.com/track. No action needed."
            ),
        },
    )
    case_id = created.json()["case"]["id"]
    response = client.post(f"/case/{case_id}/recon")
    assert response.status_code == 422  # recon is reserved for HIGH-risk cases


def test_sandbox_recon_high_risk_refuses_offline(client):
    created = client.post("/case", json={"input_type": "text", "text": SCAM_TEXT})
    case_id = created.json()["case"]["id"]

    response = client.post(f"/case/{case_id}/recon")
    assert response.status_code == 200
    payload = response.json()
    # Offline CI: the probe must REFUSE explicitly — never crash, never leak,
    # never pretend. The refusal itself is stored as evidence.
    assert payload["status"] == "refused"
    assert "offline" in payload["detail"].lower()
    assert "ALLOW_OUTBOUND_LOOKUPS" in payload["detail"]


def test_intel_match_fires_on_previously_reported_url(client):
    """Report a case, then submit the same URL again — the new case must get
    the GLOBAL THREAT INTEL MATCH cue and a HIGH score (persistence check:
    matching works against the SQLite-backed store, not session memory)."""
    scam_text = (
        "SINGPOST: parcel HELD, pay the delivery fee: https://intel-match-check.example/9x2 "
        "— confirm your IC number and OTP. Urgent!"
    )
    first = client.post("/case", json={"input_type": "text", "text": scam_text})
    case_id = first.json()["case"]["id"]
    decided = client.post(
        f"/case/{case_id}/decision",
        json={"human_action": "report", "decided_by": "pytest"},
    )
    assert decided.status_code == 200  # this reports the indicator hashes

    second = client.post(
        "/case",
        json={"input_type": "text", "text": scam_text},
    )
    assert second.status_code == 200
    body = second.json()
    cue_types = {cue["cue_type"] for cue in body["verdict"]["cues"]}
    assert "threat_intel_match" in cue_types
    assert body["verdict"]["score"] == "high"
    match_evidence = [e for e in body["evidence"] if e["tool"] == "community_intel_match"]
    assert match_evidence, "intel match must be logged as evidence"
    assert body["verdict"]["cues"][0]["cue_type"] == "threat_intel_match"
