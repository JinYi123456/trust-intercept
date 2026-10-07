"""Decision Defence Engine for TRUST//INTERCEPT.

The legacy prototype answered mostly "how risky is this?".  This layer answers
three operational questions before a person acts:

1. What decision is the sender trying to force?
2. What evidence would have to be true for the message to be legitimate?
3. What independent verification step breaks the attacker's chain?

All outputs are deterministic and auditable.  No LLM is required.
"""
from __future__ import annotations

from typing import Any


def _has(cues: list[dict[str, Any]], *types: str) -> bool:
    wanted = set(types)
    return any(str(c.get("cue_type", "")) in wanted for c in cues if isinstance(c, dict))


def build_defence_plan(
    *,
    redacted_text: str,
    cues: list[dict[str, Any]],
    radar: dict[str, Any],
    risk: str,
    confidence: str,
    domains: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the explainable decision-defence object shown to the human."""
    cues = cues or []
    domains = domains or []

    payment = _has(cues, "payment_request", "urgent_wire_transfer")
    credential = _has(cues, "credential_request", "otp_request")
    link = _has(cues, "disguised_link", "url_shortener", "brand_impersonation")
    urgency = _has(cues, "urgency_pressure", "threat_language")
    authority = _has(cues, "authority_spoof", "brand_impersonation", "spoofed_sender")
    reward = _has(cues, "too_good_to_be_true", "prize_bait")

    actions: list[str] = []
    if payment:
        actions.append("send_money_or_pay")
    if credential:
        actions.append("reveal_credentials_or_otp")
    if link:
        actions.append("open_or_follow_a_link")
    if not actions and (urgency or authority):
        actions.append("act_without_independent_verification")
    if not actions:
        actions.append("continue_the_conversation")

    chain: list[dict[str, str]] = [
        {"id": "message", "label": "SUSPICIOUS MESSAGE", "kind": "source"},
    ]
    if authority:
        chain.append({"id": "authority", "label": "BORROWED AUTHORITY", "kind": "manipulation"})
    if urgency:
        chain.append({"id": "urgency", "label": "TIME PRESSURE", "kind": "manipulation"})
    if payment:
        chain.append({"id": "payment", "label": "PAYMENT", "kind": "requested_action"})
    if credential:
        chain.append({"id": "credential", "label": "OTP / CREDENTIALS", "kind": "requested_action"})
    if link:
        chain.append({"id": "link", "label": "DESTINATION", "kind": "requested_action"})
    if not (authority or urgency or payment or credential or link):
        chain.append({"id": "action", "label": "REQUESTED ACTION", "kind": "requested_action"})

    edges = [
        {"from": chain[i]["id"], "to": chain[i + 1]["id"], "reason": "observed attack sequence"}
        for i in range(len(chain) - 1)
    ]

    if payment or credential:
        safe_steps = [
            "PAUSE — do not pay, transfer, or enter any OTP/password/card details.",
            "Open the organisation's official app or manually type its official website.",
            "Verify the case/order/account using information you already know, not the suspicious message.",
        ]
    elif link:
        safe_steps = [
            "PAUSE — do not open the supplied destination in your normal browser.",
            "Find the organisation's official website/app independently.",
            "Compare the legitimate service or tracking status there.",
        ]
    else:
        safe_steps = [
            "PAUSE — do not let the sender's urgency determine the next action.",
            "Verify the sender through an independent, trusted channel.",
        ]

    if risk == "high" or float(radar.get("overall") or 0) >= 0.65:
        recommendation = "PAUSE"
    elif risk == "medium" or confidence == "low":
        recommendation = "VERIFY"
    else:
        recommendation = "VERIFY"

    evidence_count = len(cues) + len(domains)
    evidence_coverage = min(100, 30 + evidence_count * 8)
    manipulation_pressure = round(float(radar.get("overall") or 0) * 100)
    uncertainty_penalty = 20 if confidence == "low" else 8 if confidence == "medium" else 0
    false_positive_guard = 15 if not cues else 8
    decision_safety_score = max(
        0,
        min(100, round(55 + evidence_coverage * 0.25 + manipulation_pressure * 0.20 - uncertainty_penalty + false_positive_guard)),
    )

    counterfactual = {
        "question": "What would have to be true for this message to be legitimate?",
        "conditions": [
            "The claimed organisation independently confirms the request.",
            "The official channel shows the same case, order, payment or account event.",
            "No sensitive credential or OTP is requested through an untrusted channel.",
        ],
        "how_to_try_to_disprove_us": "Use a trusted official channel that was not supplied by the suspicious message.",
    }

    return {
        "intended_actions": actions,
        "attack_chain": {"nodes": chain, "edges": edges},
        "counterfactual": counterfactual,
        "safe_verification": safe_steps,
        "recommendation": recommendation,
        "decision_safety_score": decision_safety_score,
        "metrics": {
            "evidence_coverage": evidence_coverage,
            "manipulation_pressure": manipulation_pressure,
            "false_positive_guard": false_positive_guard,
            "uncertainty_penalty": uncertainty_penalty,
        },
        "method": "deterministic decision-defence rules; no LLM dependency",
        "privacy_note": "Analysis uses the redacted case representation; original PII is not included in this object.",
    }
