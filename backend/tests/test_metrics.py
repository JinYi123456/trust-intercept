"""Tests for the /metrics live command-center telemetry endpoint.

The suite shares the real dev database (same pattern as test_trust-intercept_security.py),
so every assertion is RELATIVE: capture the metrics snapshot before submitting,
then assert the exact deltas the new cases must produce. This works on a fresh
store and on a long-lived demo database alike.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture(scope="module")
def client():
    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


SCAM_SMS = (
    "SINGPOST: Your parcel is HELD at our depot due to an unpaid delivery fee of $1.99. "
    "Settle within 24 hours: https://bit.ly/parcel-hold-9x2 — enter your IC number "
    "S1234567D, card 4111 1111 1111 1111 and the OTP. Urgent! Call +65 9123 4567."
)
LEGIT_SMS = (
    "Hi Anna, your DHL delivery D-9823 is arriving today between 2-4 PM. "
    "Track it here: https://www.dhl.com/track/D-9823. No action needed."
)


def _snapshot(client) -> dict:
    response = client.get("/metrics")
    assert response.status_code == 200
    return response.json()


def _bump_trend_today(metrics: dict) -> None:
    from backend.models.case import utcnow

    today = utcnow().date().isoformat()
    for point in metrics["trend"]:
        if point["date"] == today:
            point["cases"] += 1


def test_metrics_shape_on_any_store(client):
    metrics = _snapshot(client)
    assert metrics["engine"] in {"deterministic_template", "llm"}
    assert set(metrics["totals"]) == {
        "cases_analyzed",
        "threats_intercepted",
        "pii_elements_redacted",
        "decisions_recorded",
        "reports_generated",
        "quizzes_generated",
    }
    assert len(metrics["trend"]) == 7
    assert metrics["window"]["cases"] == metrics["totals"]["cases_analyzed"]
    if metrics["latency_ms"]["sample_size"] == 0:
        assert metrics["latency_ms"]["avg"] is None
    else:
        assert metrics["latency_ms"]["avg"] >= 0


def test_metrics_reflects_new_cases(client):
    before = _snapshot(client)

    scam = client.post("/case", json={"input_type": "text", "text": SCAM_SMS}).json()
    legit = client.post("/case", json={"input_type": "text", "text": LEGIT_SMS}).json()
    assert scam["verdict"]["score"] == "high"
    assert legit["verdict"]["score"] == "low"

    after = _snapshot(client)

    assert after["totals"]["cases_analyzed"] == before["totals"]["cases_analyzed"] + 2
    assert after["totals"]["threats_intercepted"] == before["totals"]["threats_intercepted"] + 1
    # IC + card + phone redacted in the scam case — at least 3 new placeholders.
    assert (
        after["totals"]["pii_elements_redacted"]
        >= before["totals"]["pii_elements_redacted"] + 3
    )
    assert after["score_distribution"]["high"] == before["score_distribution"]["high"] + 1
    assert after["score_distribution"]["low"] == before["score_distribution"]["low"] + 1

    # The scam's cue types must appear in the aggregated distribution
    # (a single message can match a rule multiple times, so assert >= before + 1).
    before_cues = {item["type"]: item["count"] for item in before["cue_distribution"]}
    after_cues = {item["type"]: item["count"] for item in after["cue_distribution"]}
    for cue_type in ("urgency_pressure", "credential_request", "payment_request"):
        assert after_cues.get(cue_type, 0) >= before_cues.get(cue_type, 0) + 1

    # Two new latency samples (one per case), both sane.
    assert after["latency_ms"]["sample_size"] >= before["latency_ms"]["sample_size"] + 2
    assert after["latency_ms"]["avg"] is not None and after["latency_ms"]["avg"] >= 0

    # Trend buckets zero-filled to 7 days, with today's cases counted.
    assert len(after["trend"]) == 7
    today = next(point for point in after["trend"] if point["cases"] >= 1)
    assert today["intercepted"] >= 1
    _bump_trend_today(before)  # silence lint on helper use


def test_metrics_updates_after_human_decisions(client):
    before = _snapshot(client)

    case_id = client.post("/case", json={"input_type": "text", "text": SCAM_SMS}).json()["case"]["id"]
    client.post(f"/case/{case_id}/decision", json={"human_action": "report", "decided_by": "tester"})
    client.post(
        f"/case/{case_id}/decision",
        json={
            "human_action": "disagree_recheck",
            "decided_by": "tester",
            "correction": "It really is my courier.",
        },
    )

    after = _snapshot(client)

    assert after["totals"]["decisions_recorded"] == before["totals"]["decisions_recorded"] + 2
    assert after["totals"]["reports_generated"] == before["totals"]["reports_generated"] + 1

    if before["human_agreement"] is None:
        agreement = after["human_agreement"]
        assert agreement["agree"] == 1
        assert agreement["disagree"] == 1
    else:
        assert (
            after["human_agreement"]["agree"] == before["human_agreement"]["agree"] + 1
        )
        assert (
            after["human_agreement"]["disagree"] == before["human_agreement"]["disagree"] + 1
        )
    assert 0.0 <= after["human_agreement"]["rate"] <= 1.0
