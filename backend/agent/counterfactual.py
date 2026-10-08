"""Counterfactual Verification Engine for TRUST//INTERCEPT.

Turns the question "If this were legitimate, what would independently prove it?"
into a structured, auditable verification task. This module never opens a URL,
contacts a sender, or invents external confirmation.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _has(cues: list[dict[str, Any]], *types: str) -> bool:
    wanted = set(types)
    return any(str(c.get("cue_type", "")) in wanted for c in cues if isinstance(c, dict))


def _domain_status(domains: list[dict[str, Any]]) -> tuple[str, list[str]]:
    if not domains:
        return "NOT_CHECKED", []
    notes: list[str] = []
    checked = False
    contradictions = 0
    support = 0
    for item in domains:
        for rep in item.get("reputation", []) or []:
            if rep.get("checked"):
                checked = True
                if rep.get("malicious"):
                    contradictions += 1
                elif rep.get("detail"):
                    support += 1
        if item.get("domain_age_days") is not None:
            notes.append(f"Domain age observed: {item['domain_age_days']} days.")
    if contradictions:
        return "CONTRADICTS", notes + ["A reputation check flagged the destination as malicious."]
    if checked and support:
        return "SUPPORTS", notes + ["Available reputation checks did not produce a malicious finding."]
    return "INCONCLUSIVE", notes


def build_counterfactual_verification(
    *,
    redacted_text: str,
    cues: list[dict[str, Any]],
    defence_plan: dict[str, Any],
    domains: list[dict[str, Any]] | None = None,
    link_result: dict[str, Any] | None = None,
    risk: str = "low",
) -> dict[str, Any]:
    """Create a verification task without claiming verification that did not happen."""
    cues = cues or []
    domains = domains or []
    link_result = link_result or {}

    payment = _has(cues, "payment_request", "urgent_wire_transfer")
    credential = _has(cues, "credential_request", "otp_request")
    link = bool(link_result.get("urls") or domains) or _has(cues, "disguised_link", "url_shortener", "brand_impersonation")
    authority = _has(cues, "authority_spoof", "brand_impersonation", "spoofed_sender")

    claims: list[str] = []
    sources: list[str] = []
    expected: list[str] = []
    if payment:
        claims.append("The requested payment or transfer is legitimate.")
        sources.append("Official organisation app/account portal opened independently")
        expected.append("The same invoice, case, order, or payment request appears in the official channel.")
    if credential:
        claims.append("The request for credentials or an OTP is legitimate.")
        sources.append("Official security/support channel reached independently")
        expected.append("The organisation independently confirms the security event without asking for the OTP through this message.")
    if link:
        claims.append("The supplied destination represents the claimed organisation or service.")
        sources.append("Official website/app reached by manual navigation, not the supplied link")
        expected.append("The official channel contains the same service, case, or tracking information and does not require the suspicious destination.")
    if authority:
        claims.append("The sender really represents the claimed organisation or person.")
        sources.append("Known contact method or official directory")
        expected.append("The independent channel confirms the sender's identity and the request.")
    if not claims:
        claims.append("The sender's claim is legitimate and safe to act on.")
        sources.append("A trusted channel already known to the user")
        expected.append("The independent channel confirms the same claim without relying on this message.")

    domain_state, domain_notes = _domain_status(domains)
    findings: list[dict[str, Any]] = []
    if domains:
        findings.append({
            "claim": "The destination is safe enough to support the sender's claim.",
            "source": "Automated domain/reputation checks",
            "expected_if_legitimate": "No malicious reputation finding and a destination consistent with the claimed service.",
            "actual_evidence": domain_notes or ["Domain intelligence was available but did not establish legitimacy."],
            "state": domain_state,
            "risk_delta": 2 if domain_state == "CONTRADICTS" else -1 if domain_state == "SUPPORTS" else 0,
        })

    findings.append({
        "claim": claims[0],
        "source": sources[0],
        "expected_if_legitimate": expected[0],
        "actual_evidence": ["NOT CHECKED — this requires an independent channel and human action."],
        "state": "NOT_CHECKED",
        "risk_delta": 0,
    })

    overall = "CONTRADICTS" if any(f["state"] == "CONTRADICTS" for f in findings) else (
        "SUPPORTS" if findings and all(f["state"] == "SUPPORTS" for f in findings) else "INCONCLUSIVE"
    )
    if any(f["state"] == "NOT_CHECKED" for f in findings):
        overall = "NOT_CHECKED" if all(f["state"] == "NOT_CHECKED" for f in findings) else overall

    total_delta = sum(int(f.get("risk_delta", 0)) for f in findings)
    if total_delta > 0:
        impact = "RAISE_RISK"
    elif total_delta < 0:
        impact = "LOWER_RISK_ONLY_AFTER_HUMAN_REVIEW"
    else:
        impact = "NO_AUTOMATIC_RISK_CHANGE"

    verification_action = [
        "Do not use the suspicious message's link, phone number, QR destination, or reply address for verification.",
        f"Use: {sources[0]}.",
        "Compare the independent result with the exact claim above.",
        "If the independent channel cannot confirm it, treat the claim as unverified and do not proceed with the requested action.",
    ]

    return {
        "engine": "counterfactual_verification_v1",
        "question": "If this were legitimate, what independent evidence should exist?",
        "claim_under_test": claims[0],
        "claims": claims,
        "independent_sources": sources,
        "expected_evidence": expected,
        "findings": findings,
        "overall_state": overall,
        "risk_impact": impact,
        "risk_delta": total_delta,
        "safe_verification_action": verification_action,
        "human_required": True,
        "network_action_taken": False,
        "safety_boundary": "No suspicious URL was opened and no sender was contacted by this engine.",
        "method": "deterministic evidence-state rules; no fabricated external confirmation",
        "privacy_note": "Verification uses the redacted case representation; original PII is not included.",
    }
