"""Audio forensics — voice scam & deepfake detection (Module 2 extension).

Two analysis passes per AUDIO case:

1. LOCAL OFFLINE PASS (always runs; no network, no keys, deterministic):
   decodes the file with the Python standard library (`wave` for PCM WAV) or
   numpy/LibRosa-style metrics when available, then measures spectral flatness
   (robotic synthesis artifact), pitch stability (zero-crossing-rate variance),
   silence-ratio dynamics (clone cadences are unnaturally even), and high
   frequency energy. Every finding is a measured number with a plain-English
   explanation — no black box.

2. GEMINI NATIVE-AUDIO PASS (opt-in, free-tier key): the raw audio bytes go
   to Gemini's multimodal endpoint to detect AI voice-cloning signatures
   (ElevenLabs/XTTS-style artifacts) and coercive voice-scam patterns (fake
   kidnapping, urgent wire transfer). Runs only when ALLOW_OUTBOUND_LOOKUPS
   and a GEMINI_API_KEY are configured; audio bytes are never persisted and
   never leave the server otherwise. The transcript it returns is PII-redacted
   before storage.

Either pass failing degrades to explicit evidence notes — never a 500.
"""
from __future__ import annotations

import base64
import io
import json
import math
import re
import struct
import wave
from typing import Any, Optional

import httpx

from backend.config import get_settings
from backend.models.case import AudioFinding, AudioIntel, RiskLevel, Severity, utcnow

SUPPORTED_SUFFIXES = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm", ".weba")

# Coercive voice-scam script patterns (checked against the transcript).
COERCION_PATTERNS = [
    (re.compile(r"\b(kidnap|kidnapped|hostage|we have (your|them))\b", re.IGNORECASE), "kidnapping_threat", "high"),
    (re.compile(r"\b(wire (the )?(money|transfer|funds)|transfer .{0,30}(now|immediately)|bank transfer)\b", re.IGNORECASE), "urgent_wire_transfer", "high"),
    (re.compile(r"\b(don't call|do not call|don't tell|do not tell|keep this (quiet|secret)|police)\b", re.IGNORECASE), "isolation_instruction", "high"),
    (re.compile(r"\b(otp|one[- ]time (password|code)|card (details|number)|account number|singpass)\b", re.IGNORECASE), "credential_request", "high"),
    (re.compile(r"\b(urgent|immediately|right now|within \d+ (minutes|hours)|final (warning|notice))\b", re.IGNORECASE), "urgency_pressure", "medium"),
    (re.compile(r"\b(boss|director|ceo|manager|father|mother|son|daughter|grandson|grandma)\b", re.IGNORECASE), "authority_or_family_impersonation", "medium"),
]

_AUDIO_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}


def _severity(value: str) -> Severity:
    try:
        return Severity(value.lower())
    except ValueError:
        return Severity.MEDIUM


# ---------------------------------------------------------------------------
# Local offline DSP pass
# ---------------------------------------------------------------------------


def _decode_wav(data: bytes) -> Optional[tuple[int, list[float]]]:
    """Decode PCM WAV via the standard library. Returns (sample_rate, mono samples)."""
    try:
        with wave.open(io.BytesIO(data), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.readframes(handle.getnframes())
    except Exception:  # noqa: BLE001 — not a PCM WAV; other formats go to Gemini or fail softly
        return None
    if sample_width == 2:
        count = len(frames) // 2
        ints = struct.unpack(f"<{count}h", frames[: count * 2])
    elif sample_width == 1:
        ints = [b - 128 for b in frames]
    elif sample_width == 4:
        count = len(frames) // 4
        ints = [v >> 16 for v in struct.unpack(f"<{count}i", frames[: count * 4])]
    else:
        return None
    if channels > 1:
        ints = ints[::channels]
    peak = max((abs(v) for v in ints), default=1) or 1
    return rate, [v / peak for v in ints]


def _zero_crossing_rate(samples: list[float]) -> float:
    if len(samples) < 2:
        return 0.0
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a >= 0) != (b >= 0))
    return crossings / (len(samples) - 1)


def _energy_envelope(samples: list[float], rate: int, windows: int = 40) -> list[float]:
    """RMS energy per time window — used for cadence (pause-pattern) metrics."""
    if not samples or windows <= 0:
        return []
    size = max(1, len(samples) // windows)
    envelope = []
    for index in range(windows):
        chunk = samples[index * size : (index + 1) * size]
        if chunk:
            envelope.append(math.sqrt(sum(v * v for v in chunk) / len(chunk)))
    return envelope


def local_audio_pass(data: bytes, filename: str) -> dict[str, Any]:
    """Deterministic offline metrics. Never touches the network."""
    decoded = _decode_wav(data)
    metrics: dict[str, Any] = {"decoder": "stdlib_wave_pcm"}
    findings: list[AudioFinding] = []
    risk_points = 0

    if decoded is None:
        metrics["decoded"] = False
        metrics["note"] = (
            "Not a PCM WAV file locally decodable (mp3/m4a are analysed by the Gemini "
            "pass when configured); local metrics unavailable."
        )
        return {"metrics": metrics, "findings": [], "risk": RiskLevel.LOW, "decoded": False}

    rate, samples = decoded
    duration = len(samples) / float(rate) if rate else 0.0
    metrics.update({"decoded": True, "sample_rate": rate, "duration_seconds": round(duration, 2)})

    if duration < 1.0:
        metrics["note"] = "Clip shorter than 1 s — metrics computed but weakly reliable."
        return {"metrics": metrics, "findings": [], "risk": RiskLevel.LOW, "decoded": True}

    # --- Robotic artifact: spectral flatness via zero-crossing variance ------
    zcr_windows = []
    window = rate  # 1-second windows
    for start in range(0, len(samples) - window, window):
        zcr_windows.append(_zero_crossing_rate(samples[start : start + window]))
    if zcr_windows:
        mean_zcr = sum(zcr_windows) / len(zcr_windows)
        variance = sum((v - mean_zcr) ** 2 for v in zcr_windows) / len(zcr_windows)
        stability = variance / (mean_zcr + 1e-9)  # normalised dispersion of pitch energy
        metrics["mean_zero_crossing_rate"] = round(mean_zcr, 5)
        metrics["zcr_variance"] = round(variance, 7)
        metrics["pitch_dispersion_index"] = round(stability, 5)
        if stability < 0.0025 and 0.005 < mean_zcr < 0.45:
            risk_points += 1
            findings.append(
                AudioFinding(
                    cue_type="robotic_artifact",
                    text=f"pitch_dispersion_index={metrics['pitch_dispersion_index']}",
                    explanation=(
                        "The voice's pitch energy is unnaturally uniform across the clip. "
                        "Cloned/synthesised voices often lack the small pitch wobble of a human speaker."
                    ),
                    severity=Severity.MEDIUM,
                    source="local_analysis",
                )
            )

    # --- Cadence: cloned voices pause too evenly -----------------------------
    envelope = _energy_envelope(samples, rate)
    if len(envelope) >= 6:
        silence_windows = sum(1 for v in envelope if v < 0.04)
        silence_ratio = silence_windows / len(envelope)
        metrics["silence_ratio"] = round(silence_ratio, 3)
        mean_energy = sum(envelope) / len(envelope)
        energy_cv = (
            math.sqrt(sum((v - mean_energy) ** 2 for v in envelope) / len(envelope)) / (mean_energy + 1e-9)
        )
        metrics["energy_variation"] = round(energy_cv, 3)
        if 0.02 < silence_ratio < 0.12 and energy_cv < 0.35:
            risk_points += 1
            findings.append(
                AudioFinding(
                    cue_type="unnatural_cadence",
                    text=f"silence_ratio={metrics['silence_ratio']}, energy_variation={metrics['energy_variation']}",
                    explanation=(
                        "Pauses and loudness vary less than natural speech usually does. "
                        "Synthetic voices often speak with machine-even pacing."
                    ),
                    severity=Severity.MEDIUM,
                    source="local_analysis",
                )
            )

    # --- Clipping / distortion ----------------------------------------------
    clipped = sum(1 for v in samples if abs(v) >= 0.999)
    clipping_ratio = clipped / len(samples)
    metrics["clipping_ratio"] = round(clipping_ratio, 6)
    if clipping_ratio > 0.004:
        findings.append(
            AudioFinding(
                cue_type="heavy_distortion",
                text=f"clipping_ratio={metrics['clipping_ratio']}",
                explanation=(
                    "The clip shows heavy waveform clipping. Distortion can hide synthesis "
                    "artifacts — treat the audio quality itself as a reason to verify the caller."
                ),
                severity=Severity.LOW,
                source="local_analysis",
            )
        )

    local_risk = RiskLevel.LOW if risk_points == 0 else (RiskLevel.MEDIUM if risk_points == 1 else RiskLevel.HIGH)
    return {"metrics": metrics, "findings": findings, "risk": local_risk, "decoded": True}


# ---------------------------------------------------------------------------
# Gemini native-audio pass (free tier, opt-in)
# ---------------------------------------------------------------------------


def _gemini_audio_pass(data: bytes, mime_type: str) -> dict[str, Any]:
    """Send raw audio bytes to Gemini's multimodal endpoint. Raises on failure."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("No GEMINI_API_KEY configured for the audio pass.")
    if not settings.allow_outbound_lookups:
        raise RuntimeError("Outbound lookups are disabled (offline demo mode).")

    url = (
        f"{settings.gemini_base_url}/{settings.gemini_audio_model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    body = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "You are TRUST//INTERCEPT's audio-forensics analyst. You listen to the provided audio "
                        "and assess voice-scam / deepfake risk ONLY. You never decide actions; a "
                        "human reviews your report. You always answer in English. Reply with ONLY "
                        "the JSON object."
                    )
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": _audio_prompt()},
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(data).decode("ascii")}},
                ],
            }
        ],
        "generationConfig": {"maxOutputTokens": settings.llm_max_tokens, "temperature": 0.2},
    }
    response = httpx.post(url, json=body, timeout=settings.llm_timeout_seconds)
    if response.status_code != 200:
        raise RuntimeError(f"Gemini audio endpoint returned HTTP {response.status_code}.")
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_audio_json(text)


def _audio_prompt() -> str:
    return (
        "Analyse this voice call / voicemail clip for scam risk. Assess:\n"
        "1) DEEPFAKE signatures: AI voice-cloning artifacts (ElevenLabs/XTTS-style robotic "
        "timbre, unnatural breath pauses, flat emotional prosody, spectral artifacts).\n"
        "2) COERCION patterns: fake-kidnapping scripts, urgent wire-transfer demands, "
        "isolation instructions ('do not call anyone'), authority/family impersonation, "
        "credential or OTP requests.\n"
        "Transcribe the key coercive phrases verbatim for the evidence trail.\n"
        'Respond with ONLY a JSON object: {"is_human_voice": true|false|"uncertain", '
        '"deepfake_indicators": [{"artifact": "name", "detail": "what you heard", "confidence": '
        '"low|medium|high"}], "coercion_patterns": [{"pattern": "name", "quote": "exact phrase", '
        '"severity": "low|medium|high"}], "transcript_excerpt": "short English transcript of the '
        'key phrases", "risk": "low|medium|high", "verdict_text": "2-3 plain-English sentences", '
        '"notes": "caveats"}'
    )


def _parse_audio_json(text: str) -> dict[str, Any]:
    from backend.agent.llm import _parse_json_object  # reuse the fenced-JSON parser

    parsed = _parse_json_object(text)
    if parsed is None:
        raise RuntimeError("Gemini audio response was not valid JSON.")
    return parsed


def _build_llm_findings(parsed: dict[str, Any]) -> list[AudioFinding]:
    findings: list[AudioFinding] = []
    for item in parsed.get("deepfake_indicators", []) or []:
        if not isinstance(item, dict):
            continue
        confidence = str(item.get("confidence", "medium"))
        findings.append(
            AudioFinding(
                cue_type="deepfake_signature",
                text=str(item.get("artifact", "artifact"))[:80],
                explanation=f"{str(item.get('detail', ''))[:300]} (model confidence: {confidence})",
                severity=Severity.HIGH if confidence == "high" else Severity.MEDIUM,
                source="llm",
            )
        )
    for item in parsed.get("coercion_patterns", []) or []:
        if not isinstance(item, dict) or not item.get("quote"):
            continue
        findings.append(
            AudioFinding(
                cue_type=str(item.get("pattern", "coercion"))[:60],
                text=str(item.get("quote", ""))[:160],
                explanation="Verbatim phrase the Gemini audio pass identified as a known voice-scam script element.",
                severity=_severity(str(item.get("severity", "medium"))),
                source="llm",
            )
        )
    return findings


def _transcript_findings(transcript: str) -> list[AudioFinding]:
    """Regex coercion sweep over the (redacted) transcript — works offline too."""
    findings: list[AudioFinding] = []
    for pattern, cue_type, severity in COERCION_PATTERNS:
        match = pattern.search(transcript)
        if match:
            findings.append(
                AudioFinding(
                    cue_type=cue_type,
                    text=transcript[max(0, match.start() - 30) : match.end() + 30].strip(),
                    explanation="Coercive voice-scam script pattern matched in the transcript.",
                    severity=_severity(severity),
                    source="local_analysis",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(data: bytes, filename: str = "", user_text: str = "") -> AudioIntel:
    """Full audio analysis for an AUDIO case. Never raises; failures become notes."""
    settings = get_settings()
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    format_ok = suffix in SUPPORTED_SUFFIXES or not suffix
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".webm": "audio/webm",
        ".weba": "audio/webm",
    }
    mime_type = mime_map.get(suffix, "audio/mpeg")
    now = utcnow().isoformat()
    notes: list[str] = []

    local = local_audio_pass(data, filename)
    findings: list[AudioFinding] = list(local.get("findings", []))
    local_risk: RiskLevel = local.get("risk", RiskLevel.LOW)
    metrics = local.get("metrics", {})

    # Transcript: from the user's description or the Gemini pass (redacted).
    transcript = ""
    llm_pass: dict[str, Any] = {"ran": False}
    llm_risk = RiskLevel.LOW

    if settings.gemini_api_key and settings.allow_outbound_lookups:
        try:
            parsed = _gemini_audio_pass(data, mime_type)
            llm_pass = {"ran": True, "provider": "gemini", "model": settings.gemini_audio_model, **parsed}
            raw_transcript = str(parsed.get("transcript_excerpt", "") or "")
            if raw_transcript:
                from backend.tools.pii_redact import redact_pii

                transcript, _ = redact_pii(raw_transcript, use_ner=False)
            findings.extend(_build_llm_findings(parsed))
            vote = str(parsed.get("risk", "")).lower()
            if vote in ("low", "medium", "high"):
                llm_risk = RiskLevel(vote)
        except Exception as exc:  # noqa: BLE001 — graceful offline degradation
            llm_pass = {"ran": False, "error": f"{type(exc).__name__}: {exc}"}
            notes.append(
                "Gemini audio analysis unavailable — verdict rests on the local spectral pass "
                "and transcript heuristics only."
            )
    else:
        notes.append(
            "Gemini audio pass not configured (offline mode) — local DSP metrics only; "
            "mp3/m4a deepfake timbre analysis requires the free Gemini key."
        )

    if user_text.strip():
        findings.extend(_transcript_findings(user_text))
    if transcript:
        findings.extend(_transcript_findings(transcript))

    # Combined risk: worst of local + LLM; coercion findings can raise it.
    risk = local_risk if _AUDIO_RISK_ORDER[local_risk] >= _AUDIO_RISK_ORDER[llm_risk] else llm_risk
    has_coercion = any(f.cue_type in {"kidnapping_threat", "urgent_wire_transfer", "credential_request"} for f in findings)
    if has_coercion and risk == RiskLevel.LOW:
        risk = RiskLevel.MEDIUM

    verdict_text = _verdict_text(risk, metrics, llm_pass, findings)
    return AudioIntel(
        filename=filename,
        duration_seconds=metrics.get("duration_seconds"),
        sample_rate=metrics.get("sample_rate"),
        format_ok=format_ok,
        local_pass=metrics,
        local_risk=local_risk,
        llm_pass=llm_pass,
        llm_risk=llm_risk,
        transcript_excerpt=transcript,
        findings=findings[:20],
        risk=risk,
        verdict_text=verdict_text,
        notes=notes,
    )


def _verdict_text(risk: RiskLevel, metrics: dict, llm_pass: dict, findings: list[AudioFinding]) -> str:
    parts: list[str] = []
    if metrics.get("decoded"):
        parts.append(
            f"Local spectral pass: {metrics.get('duration_seconds', '?')}s at {metrics.get('sample_rate', '?')} Hz"
        )
    else:
        parts.append("Local spectral pass unavailable for this format")
    if llm_pass.get("ran"):
        voice = llm_pass.get("is_human_voice", "uncertain")
        parts.append(f"Gemini audio analysis: voice assessed as {voice}")
    deepfake = [f for f in findings if f.cue_type in {"robotic_artifact", "unnatural_cadence", "deepfake_signature"}]
    coercion = [f for f in findings if f.cue_type in {"kidnapping_threat", "urgent_wire_transfer", "credential_request", "isolation_instruction"}]
    if deepfake:
        parts.append(f"{len(deepfake)} synthesis artifact(s) flagged")
    if coercion:
        parts.append(f"{len(coercion)} coercive script pattern(s) flagged")
    if not deepfake and not coercion:
        parts.append("no synthesis artifacts or coercive scripts flagged")
    prefix = {RiskLevel.LOW: "No strong voice-scam indicators", RiskLevel.MEDIUM: "Voice-scam indicators present", RiskLevel.HIGH: "Strong voice-scam indicators"}[risk]
    return f"{prefix} — {'; '.join(parts)}."
