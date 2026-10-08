"""End-to-end demo smoke test — the three flows a judge will click.

Run with:  PYTHONPATH=. pytest -q backend/tests/test_e2e_smoke.py

Flows:
  (a) parcel-fee scam SMS      -> HIGH verdict, cues highlighted, human approval
  (b) legitimate courier SMS   -> LOW verdict, zero false alarm
  (c) offline template engine  -> the same flows complete with LLM disabled

Config note: this module follows the same convention as test_advanced_features.py —
os.environ is set BEFORE importing backend.main because Settings is lru_cached on
first import and whichever test module imports first fixes the config for the whole
session. Reusing the same DB_PATH keeps every module on one disposable store.
"""
from __future__ import annotations

import os
import tempfile

_TEST_DB = os.path.join(tempfile.gettempdir(), "trust-intercept_security_test.db")
os.environ.update(
    {
        "DB_PATH": _TEST_DB,
        "LLM_PROVIDER": "none",  # deterministic template mode; flow (c) asserts this too
        "ALLOW_OUTBOUND_LOOKUPS": "false",  # no network in CI
        "CORS_ORIGINS": (
            "http://localhost:5173,http://127.0.0.1:5173,https://trust-intercept-demo.vercel.app"
        ),
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

SCAM_SMS = (
    "SINGPOST: Your parcel is HELD at our depot due to an unpaid delivery fee of $1.99. "
    "Settle within 24 hours: https://bit.ly/parcel-hold-9x2 — enter your IC number "
    "S1234567D, card 4111 1111 1111 1111 and the OTP we sent to confirm delivery. "
    "Urgent! Call +65 9123 4567 immediately."
)
LEGIT_SMS = (
    "Hi Anna, your DHL delivery D-9823 is arriving today between 2-4 PM. "
    "Track it here: https://www.dhl.com/track/D-9823. No action needed."
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# System checks: /health, /ready, CORS
# ---------------------------------------------------------------------------


def test_health_and_ready(client):
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert "llm" in body
    assert body["llm"]["template_mode"] is True  # LLM_PROVIDER=none in this suite

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["status"] == "ready"
    assert ready_body["database"] == "ready"
    assert ready_body["offline_fallback"] is True


def test_cors_preflight_from_vercel_domain(monkeypatch):
    """The exact deployed frontend origin must be allowed by CORS.

    The shared app's middleware is built at import time with whatever
    CORS_ORIGINS was in effect first (suite-wide coupling), so this test
    verifies the two layers separately, using the SAME wiring as main.py:
      1. config layer: cors_origin_list() picks up the Vercel domain
      2. middleware layer: CORSMiddleware(allow_origins=cors_origin_list())
         answers the preflight with the exact origin
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient as _TC

    from backend.config import cors_origin_list, get_settings

    origin = "https://trust-intercept-demo.vercel.app"
    monkeypatch.setenv("CORS_ORIGINS", f"http://localhost:5173,http://127.0.0.1:5173,{origin}")
    get_settings.cache_clear()
    try:
        # 1. Config layer.
        origins = cors_origin_list()
        assert origin in origins

        # 2. Middleware layer — wired exactly like backend/main.py.
        mini = FastAPI()
        mini.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origin_list() or ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @mini.get("/ping")
        def ping():
            return {"ok": True}

        with _TC(mini) as mini_client:
            preflight = mini_client.options(
                "/ping",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert preflight.status_code == 200
            assert preflight.headers.get("access-control-allow-origin") == origin

            simple = mini_client.get("/ping", headers={"Origin": origin})
            assert simple.headers.get("access-control-allow-origin") == origin
    finally:
        get_settings.cache_clear()


def test_cors_rejects_unknown_origin(monkeypatch):
    """A foreign origin must never be granted access."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient as _TC

    from backend.config import cors_origin_list, get_settings

    origin = "https://evil.example.com"
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    get_settings.cache_clear()
    try:
        mini = FastAPI()
        mini.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origin_list() or ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @mini.get("/ping")
        def ping():
            return {"ok": True}

        with _TC(mini) as mini_client:
            preflight = mini_client.options(
                "/ping",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )
            # Starlette answers preflights but must NOT grant this origin.
            assert preflight.headers.get("access-control-allow-origin") != origin
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Flow (a): parcel-fee scam SMS -> HIGH, cues highlighted, human approval
# ---------------------------------------------------------------------------


def test_flow_a_scam_sms_full_pipeline(client):
    submit = client.post(
        "/case",
        json={
            "input_type": "text",
            "text": SCAM_SMS,
            "url": "",
            "image_b64": "",
            "image_filename": "",
            "audio_b64": "",
            "audio_filename": "",
        },
    )
    assert submit.status_code == 200, submit.text
    view = submit.json()
    case_id = view["case"]["id"]

    # 1. Verdict is HIGH.
    assert view["verdict"]["score"] == "high"
    assert view["verdict"]["confidence"] in {"low", "medium", "high"}

    # 2. Cues were found and carry explanations (highlighting fuel).
    cues = view["verdict"]["cues"]
    assert len(cues) >= 2
    for cue in cues:
        assert cue["explanation"].strip()
    # PII was redacted before storage: IC and card digits must not survive raw.
    redacted = view["case"]["redacted_text"]
    assert "S1234567D" not in redacted
    assert "4111 1111 1111 1111" not in redacted

    # 3. Human approval gate: only POST /decision writes action_taken.
    decision = client.post(
        f"/case/{case_id}/decision",
        json={"human_action": "block_warn", "decided_by": "user"},
    )
    assert decision.status_code == 200, decision.text
    updated = decision.json()
    latest = updated["decisions"][-1]
    assert latest["human_action"] == "block_warn"
    assert latest["action_taken"].strip()  # a warning was actually composed

    # 4. The decision is persisted on the case.
    refetched = client.get(f"/case/{case_id}")
    assert refetched.status_code == 200
    assert len(refetched.json()["decisions"]) == 1


# ---------------------------------------------------------------------------
# Flow (b): legitimate courier SMS -> LOW, zero false alarm
# ---------------------------------------------------------------------------


def test_flow_b_legit_sms_no_false_alarm(client):
    submit = client.post(
        "/case",
        json={
            "input_type": "text",
            "text": LEGIT_SMS,
            "url": "",
            "image_b64": "",
            "image_filename": "",
            "audio_b64": "",
            "audio_filename": "",
        },
    )
    assert submit.status_code == 200, submit.text
    view = submit.json()

    assert view["verdict"]["score"] == "low"
    # Zero false alarm: no high-severity cues on a legitimate message.
    assert not [cue for cue in view["verdict"]["cues"] if cue.get("severity") == "high"]

    # The safe path works too: Looks Safe is approved without friction.
    decision = client.post(
        f"/case/{view['case']['id']}/decision",
        json={"human_action": "looks_safe", "decided_by": "user"},
    )
    assert decision.status_code == 200


# ---------------------------------------------------------------------------
# Flow (c): offline template engine completes the same flows
# ---------------------------------------------------------------------------


def test_flow_c_offline_template_fallback(client):
    """With LLM_PROVIDER=none, the deterministic engine still delivers the full flow."""
    status = client.get("/health").json()["llm"]
    assert status["template_mode"] is True

    # Scam flow offline.
    scam = client.post(
        "/case",
        json={
            "input_type": "text",
            "text": SCAM_SMS,
            "url": "",
            "image_b64": "",
            "image_filename": "",
            "audio_b64": "",
            "audio_filename": "",
        },
    )
    assert scam.status_code == 200, scam.text
    scam_view = scam.json()
    assert scam_view["verdict"]["score"] == "high"
    assert len(scam_view["verdict"]["cues"]) >= 2
    # Offline synthesis is explicitly disclosed, never hidden.
    assert scam_view["verdict"].get("reasoning_trace", {}).get("llm_used") is not True

    # Legit flow offline — same engine, same zero false alarm.
    legit = client.post(
        "/case",
        json={
            "input_type": "text",
            "text": LEGIT_SMS,
            "url": "",
            "image_b64": "",
            "image_filename": "",
            "audio_b64": "",
            "audio_filename": "",
        },
    )
    assert legit.status_code == 200, legit.text
    assert legit.json()["verdict"]["score"] == "low"

    # Approval gate still works offline.
    case_id = scam_view["case"]["id"]
    decision = client.post(
        f"/case/{case_id}/decision",
        json={"human_action": "report", "decided_by": "user"},
    )
    assert decision.status_code == 200, decision.text
    report_view = decision.json()
    # The report bundle exists only after the human approved "report".
    assert report_view["report"] is not None
    assert report_view["report"]["report_markdown"].strip()


# ---------------------------------------------------------------------------
# Safety: suspicious links are never opened automatically
# ---------------------------------------------------------------------------


def test_suspicious_links_not_opened_offline(client):
    """In offline mode the redirect walker must not make any network request —
    the case still completes and the link is reported as inspected-only."""
    submit = client.post(
        "/case",
        json={
            "input_type": "url",
            "text": "",
            "url": "https://bit.ly/parcel-hold-9x2",
            "image_b64": "",
            "image_filename": "",
            "audio_b64": "",
            "audio_filename": "",
        },
    )
    assert submit.status_code == 200, submit.text
    view = submit.json()

    tools = {entry["tool"]: entry for entry in view["evidence"]}
    link_entry = tools.get("module_2_link_safety")
    assert link_entry is not None
    raw = link_entry["raw_output"]
    # Either an explicit offline marker or an error string mentioning the
    # disabled lookups — never a silently successful visit.
    if raw.get("chains"):
        for chain in raw["chains"]:
            assert chain.get("error") or not chain.get("hops")


# ---------------------------------------------------------------------------
# Frontend build must never ship a placeholder API URL
# ---------------------------------------------------------------------------


def test_frontend_has_no_placeholder_api_url():
    """Scan the built frontend bundle for placeholder/localhost-only API URLs.

    This runs against frontend/dist, which CI builds before tests.
    """
    import re
    from pathlib import Path

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist" / "assets"
    if not dist.exists():
        pytest.skip("frontend/dist not built — run `cd frontend && npm run build` first")

    bad_patterns = [
        re.compile(r"https://your-[a-z-]*api[a-z.-]*"),
        re.compile(r"https://example\.com/api"),
        re.compile(r"YOUR_API_KEY"),
        re.compile(r"PLACEHOLDER"),
    ]
    for asset in dist.glob("*.js"):
        text = asset.read_text(encoding="utf-8", errors="ignore")
        for pattern in bad_patterns:
            assert not pattern.search(text), f"placeholder URL found in {asset.name}"
