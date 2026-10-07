"""Psychological Manipulation Radar — annotates cues with attack vectors.

Maps the concrete cues Module 1/2 detected onto named psychological attack
vectors with rule-derived confidence scores, e.g.:

    Authority Impersonation: 90%   (basis: "SINGPOST" brand claim)
    Urgency Pressure: 85%          (basis: "within 24 hours")

Design rules:
- Every score is DETERMINISTIC (rule-derived from matched cues) — the same
  evidence always produces the same radar, offline or online.
- Every vector carries its evidence basis (the cue that fired), so the UI can
  show WHY the radar says 90% and the human can overrule it.
- When the overall pressure crosses the high threshold, the radar requests a
  10-second COOLING-OFF BARRIER before any high-risk action on the Review
  screen — a deliberate friction point against urgency-based manipulation.
"""
from __future__ import annotations

from typing import Any

# cue_type -> (vector name, base score, per-extra-cue increment, ceiling)
VECTOR_RULES = {
    "urgency_pressure": ("Urgency Pressure", 0.75, 0.10, 0.95),
    "credential_request": ("Credential Harvesting", 0.85, 0.05, 0.95),
    "payment_request": ("Financial Pressure", 0.75, 0.10, 0.95),
    "authority_spoof": ("Authority Impersonation", 0.90, 0.05, 0.98),
    "spoofed_sender": ("Authority Impersonation", 0.80, 0.10, 0.95),
    "brand_impersonation": ("Authority Impersonation", 0.80, 0.10, 0.95),
    "too_good_to_be_true": ("Reward Baiting", 0.80, 0.10, 0.95),
    "prize_bait": ("Reward Baiting", 0.80, 0.10, 0.95),
    "threat_language": ("Fear & Threat", 0.85, 0.10, 0.95),
    "kidnapping_threat": ("Fear & Threat", 0.98, 0.0, 0.98),
    "isolation_instruction": ("Social Isolation", 0.90, 0.05, 0.98),
    "disguised_link": ("Deceptive Framing", 0.70, 0.10, 0.95),
    "url_shortener": ("Deceptive Framing", 0.60, 0.15, 0.90),
    "otp_request": ("Credential Harvesting", 0.85, 0.05, 0.95),
    "deepfake_signature": ("Synthetic Media Trust Abuse", 0.90, 0.05, 0.98),
    "robotic_artifact": ("Synthetic Media Trust Abuse", 0.60, 0.15, 0.90),
    "unnatural_cadence": ("Synthetic Media Trust Abuse", 0.55, 0.15, 0.90),
    "urgent_wire_transfer": ("Financial Pressure", 0.90, 0.05, 0.98),
}

COOLING_OFF_THRESHOLD = 0.65  # overall manipulation pressure that triggers the barrier


def build_radar(cues: list[dict[str, Any]]) -> dict[str, Any]:
    """Compose the radar payload from the case's merged cues (dict form)."""
    grouped: dict[str, dict[str, Any]] = {}

    for cue in cues or []:
        if not isinstance(cue, dict):
            continue
        cue_type = str(cue.get("cue_type", ""))
        rule = VECTOR_RULES.get(cue_type)
        if rule is None:
            continue
        name, base, increment, ceiling = rule
        severity = str(cue.get("severity", "medium")).lower()
        severity_bonus = {"low": 0.0, "medium": 0.05, "high": 0.10}.get(severity, 0.05)
        bucket = grouped.setdefault(
            name,
            {"name": name, "score": 0.0, "hits": 0, "basis": []},
        )
        bucket["score"] = min(ceiling, bucket["score"] + base * 0.5 + increment + severity_bonus) if bucket["hits"] else min(ceiling, base + severity_bonus)
        bucket["hits"] += 1
        quote = str(cue.get("text", ""))[:80]
        if quote and len(bucket["basis"]) < 3:
            bucket["basis"].append(quote)

    vectors = []
    for bucket in grouped.values():
        vectors.append(
            {
                "name": bucket["name"],
                "score": round(min(1.0, bucket["score"]), 2),
                "hits": bucket["hits"],
                "basis": "; ".join(f'"{b}"' for b in bucket["basis"]),
            }
        )
    vectors.sort(key=lambda item: -item["score"])

    overall = round(max((v["score"] for v in vectors), default=0.0), 2)
    return {
        "vectors": vectors[:8],
        "overall": overall,
        "cooling_off_required": overall >= COOLING_OFF_THRESHOLD,
        "threshold": COOLING_OFF_THRESHOLD,
        "method": (
            "Rule-derived deterministic scoring: each matched cue contributes to a named "
            "psychological vector; scores never depend on an LLM and are reproducible offline."
        ),
    }
