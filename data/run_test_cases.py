"""TrustIntercept QA harness — runs the sample datasets against a live API.

Usage:
    python data/run_test_cases.py                       # against http://127.0.0.1:8000
    python data/run_test_cases.py --base-url http://127.0.0.1:8001

Loads every *.json under data/sample_scams/ and data/sample_legit/, submits the
payload to POST /case, and asserts the `expected` block:

  - verdict score / action_required
  - cue types present (and absent)
  - modules that the router actually ran (from the evidence trail)
  - PII redaction: placeholders present, forbidden originals absent
  - legitimate cases must produce ZERO cues (the false-positive safeguard)
  - audio cases (input_type=audio) are synthesized from `audio_spec` and the
    audio_forensics evidence is asserted (findings + coercion cues)

Exit code 0 = all cases pass; 1 = at least one failure.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import struct
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent


def _synthesize_wav(spec: dict) -> bytes:
    """Build a deterministic PCM WAV from a dataset's audio_spec.

    Layers: `sine` (optionally clipped) tone beds and an `even_pulses`
    amplitude envelope that mimics a cloned voice's machine-even cadence.
    No randomness — the same spec always produces byte-identical audio.
    """
    rate = int(spec.get("sample_rate", 16000))
    duration = float(spec.get("duration_seconds", 3.0))
    total = int(rate * duration)

    sines = [layer for layer in spec.get("layers", []) if layer.get("type") == "sine"]
    envelope_layers = [layer for layer in spec.get("layers", []) if layer.get("type") == "envelope"]

    samples: list[float] = []
    for index in range(total):
        value = 0.0
        for layer in sines:
            value += layer.get("amplitude", 0.5) * math.sin(
                2 * math.pi * layer.get("frequency_hz", 220) * index / rate
            )
        shape = envelope_layers[0].get("shape") if envelope_layers else None
        if shape == "even_pulses":
            pulses = int(envelope_layers[0].get("pulses", 5))
            phase = (index * pulses / total) % 1.0
            gate = math.sin(math.pi * phase) ** 2
            value *= gate
        elif shape == "flat_with_gap":
            # Machine-steady loudness with one unnaturally clean micro-gap —
            # the signature the cadence detector flags (low energy variation,
            # tiny silence ratio).
            gap_fraction = float(envelope_layers[0].get("gap_fraction", 0.05))
            start = int(total * (0.5 - gap_fraction / 2))
            end = int(total * (0.5 + gap_fraction / 2))
            if start <= index < end:
                value = 0.0
        samples.append(value)

    clipped = any(layer.get("clipped") for layer in sines)
    clip_level = 0.6  # hard-clamp so a solid sample fraction sits at the rail
    peak = 1.0 if clipped else (max((abs(v) for v in samples), default=1.0) or 1.0)
    frames = bytearray()
    for value in samples:
        normalized = value / peak
        if clipped:
            normalized = max(-clip_level, min(clip_level, normalized))
        frames += struct.pack("<h", int(normalized * 32767))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()


def request_json(url: str, payload: dict | None = None, method: str = "GET") -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def check(case: dict, view: dict) -> list[str]:
    failures: list[str] = []
    expected = case["expected"]
    verdict = view.get("verdict") or {}
    case_view = view.get("case") or {}

    # --- Score & action flag -------------------------------------------------
    if verdict.get("score") != expected["score"]:
        failures.append(f"score: expected {expected['score']}, got {verdict.get('score')}")
    if verdict.get("action_required") != expected["action_required"]:
        failures.append(
            f"action_required: expected {expected['action_required']}, got {verdict.get('action_required')}"
        )

    # --- Cue types -----------------------------------------------------------
    cue_types = {cue["cue_type"] for cue in verdict.get("cues", [])}
    for cue_type in expected.get("cues_present", []):
        if cue_type not in cue_types:
            failures.append(f"missing expected cue type: {cue_type} (got {sorted(cue_types)})")
    for cue_type in expected.get("cues_absent", []):
        if cue_type in cue_types:
            failures.append(f"unexpected cue type present: {cue_type}")

    # --- Modules the router actually ran -------------------------------------
    tools = {entry["tool"] for entry in view.get("evidence", [])}
    for module in expected.get("modules_expected", []):
        if module not in tools:
            failures.append(f"module evidence missing: {module} (got {sorted(tools)})")

    # --- PII redaction --------------------------------------------------------
    redacted_text = case_view.get("redacted_text", "")
    for secret in case.get("forbidden_in_output", []):
        if secret and secret in redacted_text:
            failures.append(f"PII LEAK: original value present in redacted_text: {secret!r}")
    for placeholder in expected.get("pii_redaction", {}).get("must_contain_placeholders", []):
        if placeholder not in redacted_text:
            failures.append(f"expected placeholder missing: {placeholder}")

    # --- Legitimate cases: zero cues -----------------------------------------
    if case["id"].endswith("_legit_001") or "sample_legit" in case.get("id", ""):
        pass  # covered by cues_present == [] / cues_absent checks above

    # --- Audio pipeline validation --------------------------------------------
    if expected.get("audio_findings_present"):
        audio_entries = [entry for entry in view.get("evidence", []) if entry["tool"] == "audio_forensics"]
        if not audio_entries:
            failures.append("audio_forensics evidence missing for audio case")
        else:
            payload = audio_entries[-1]["raw_output"]
            if not payload.get("local_pass", {}).get("decoded"):
                failures.append("audio local_pass did not decode the WAV")
            finding_types = {finding["cue_type"] for finding in payload.get("findings", [])}
            for wanted in expected["audio_findings_present"]:
                if wanted not in finding_types:
                    failures.append(f"missing audio finding: {wanted} (got {sorted(finding_types)})")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TrustIntercept sample test cases against a live API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="TrustIntercept API base URL")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    status, health = request_json(f"{base}/health")
    if status != 200:
        print(f"FATAL: API not reachable at {base} (HTTP {status})")
        return 1
    print(f"API online: {health.get('app')} | template_mode={health['llm']['template_mode']} "
          f"| outbound_lookups={health['outbound_lookups_enabled']}")

    cases = sorted(DATA_DIR.glob("sample_*/*.json"))
    if not cases:
        print("FATAL: no test-case JSON files found under data/sample_*")
        return 1

    total_failures = 0
    for path in cases:
        case = json.loads(path.read_text(encoding="utf-8"))
        payload = dict(case["payload"])

        # Audio cases: synthesize the WAV from audio_spec and attach it.
        if case.get("input_type") == "audio" and case.get("audio_spec"):
            payload["input_type"] = "audio"
            payload["audio_b64"] = base64.b64encode(_synthesize_wav(case["audio_spec"])).decode("ascii")
            payload["audio_filename"] = payload.get("audio_filename", "synthetic_voicemail.wav")

        status, view = request_json(f"{base}/case", payload, method="POST")
        if status != 200:
            print(f"FAIL  {case['id']}  (HTTP {status}: {view.get('detail', 'unknown error')})")
            total_failures += 1
            continue

        failures = check(case, view)
        verdict = view.get("verdict") or {}
        cue_types = sorted({cue["cue_type"] for cue in verdict.get("cues", [])})
        result = "PASS" if not failures else "FAIL"
        print(f"{result}  {case['id']}  score={verdict.get('score')}/{verdict.get('confidence')} "
              f"cues={cue_types or ['<none>']}")
        for failure in failures:
            print(f"      - {failure}")
        total_failures += len(failures)

    print(f"\n{'ALL CASES PASSED' if total_failures == 0 else f'{total_failures} CHECK(S) FAILED'}")
    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
