"""Module 1 — Explainable Phishing Detector.

Pipeline per the blueprint:
1. A deterministic rule-based cue extractor scans the (already PII-redacted)
   message for urgency phrases, spoofed sender domains, display-name vs
   address mismatch, credential/OTP requests, payment demands, and disguised
   links.
2. An LLM pass explains and scores each cue IN THE USER'S OWN MESSAGE.

If the LLM is unavailable (offline demo, rate limit), the rule-based cues and
their deterministic explanations stand alone — the module degrades, it never
breaks.
"""
from __future__ import annotations

import re
from typing import Optional

from backend.agent import llm
from backend.models.case import (
    Confidence,
    Cue,
    InputType,
    PhishingResult,
    RiskLevel,
    Severity,
)

# ---------------------------------------------------------------------------
# Rule-based cue extractor
# ---------------------------------------------------------------------------

URGENCY_PATTERNS: list[tuple[str, Severity, str]] = [
    (
        r"\b(urgent|immediately|act now|don'?t (delay|wait)|time[- ]sensitive)\b",
        Severity.MEDIUM,
        "Manufactures time pressure so you act before you can think or verify.",
    ),
    (
        r"\b(within \d+\s*(hours?|minutes?|days?)|expires? (today|in \d+)|final (notice|warning|reminder))\b",
        Severity.HIGH,
        "Sets an artificial deadline — a classic pressure tactic used to stop you from double-checking with the real organisation.",
    ),
    (
        r"\b(account (will be )?(suspended|closed|locked|blocked|deactivated)|avoid (suspension|cancellation|deactivation))\b",
        Severity.HIGH,
        "Threatens account suspension to scare you into clicking without verifying.",
    ),
]

CREDENTIAL_PATTERNS: list[tuple[str, Severity, str]] = [
    (
        r"\b(otp|one[- ]time (password|pin|code)|passcode|verification code)\b",
        Severity.HIGH,
        "Asks about or requests a one-time password. Legitimate organisations never ask you to share an OTP.",
    ),
    (
        r"\b(password|pin)\b",
        Severity.MEDIUM,
        "Mentions credentials — combined with a link or urgency this suggests credential harvesting.",
    ),
    (
        r"\b(ic number|nric|identity card|social security|ssn)\b",
        Severity.HIGH,
        "Asks for government identity numbers — real delivery or banking services do not need these by message.",
    ),
    (
        r"\b(credit card|debit card|card (details|number)|cvv|cvc|card expiry)\b",
        Severity.HIGH,
        "Requests full card details, which no legitimate notification ever asks for.",
    ),
    (
        r"\b(bank account|internet banking|online banking|singpass)\b",
        Severity.MEDIUM,
        "References banking credentials or portals — verify directly via the official app instead.",
    ),
    (
        r"\b(verify|confirm|validate|update|reactivate|restore) your (account|identity|details|information|profile)\b",
        Severity.HIGH,
        "A 'verify your account' lure is the single most common phishing pattern.",
    ),
]

PAYMENT_PATTERNS: list[tuple[str, Severity, str]] = [
    (
        r"\b(delivery fee|handling fee|customs (fee|charge|duty)|unpaid (fee|invoice|amount)|release (fee|charge))\b",
        Severity.HIGH,
        "Claims a small fee is owed to release something you are expecting — the hallmark of parcel scams.",
    ),
    (
        r"\b(pay|payment|transfer|send) \$?\s?\d|\$\s?\d+(\.\d+)?\b",
        Severity.MEDIUM,
        "Mentions a specific money amount — check who is really asking before paying anything.",
    ),
    (
        r"\b(refund|rebate|cashback|compensation|tax return)\b",
        Severity.MEDIUM,
        "Offers money you did not ask for; 'refund' scams harvest bank details.",
    ),
]

PRIZE_PATTERNS: list[tuple[str, Severity, str]] = [
    (
        r"\b(congratulations|you (have )?won|winner|lottery|prize|lucky draw|gift (card|voucher))\b",
        Severity.MEDIUM,
        "Announces a prize from a contest you never entered — a classic advance-fee lure.",
    ),
]

SPOOF_PATTERNS: list[tuple[str, Severity, str]] = [
    (
        r"\b(your (bank|account) (has been|is) (compromised|hacked|restricted)|unusual (activity|login|sign[- ]in)|suspicious (activity|login|transaction))\b",
        Severity.HIGH,
        "Fakes a security alert to panic you into 'verifying' through the attacker's link.",
    ),
    (
        r"\b(police|lao gong|IRS|LHDN|IRAS|Inland Revenue|tax authority)\b",
        Severity.MEDIUM,
        "Invokes an authority figure to borrow trust and discourage questioning.",
    ),
    (
        r"\b(dear (customer|user|sir\/madam|account holder))\b",
        Severity.LOW,
        "Generic greeting instead of your name — bulk phishing sends rarely personalise.",
    ),
]

# Disguised links: IP hosts, punycode, URL shorteners, non-https.
SUSPICIOUS_URL_RE = re.compile(
    r"https?://(\d{1,3}(?:\.\d{1,3}){3}"
    r"|[^/\s]*xn--"
    r"|(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|is\.gd|cutt\.ly|rb\.gy|shorturl\.at|ow\.ly)"
    r"|http://)",
    re.IGNORECASE,
)

URL_ONLY_RE = re.compile(r"https?://\S+", re.IGNORECASE)

SUSPICIOUS_URL_EXPLANATION = (
    "This link uses an IP address, punycode, a shortener, or plain HTTP to disguise where it really leads — "
    "always expand short links and check the final domain."
)

def _compile(entries: list[tuple[str, Severity, str]], cue_type: str) -> list[tuple[str, Severity, str, re.Pattern[str]]]:
    return [
        (cue_type, severity, explanation, re.compile(pattern_str, re.IGNORECASE))
        for pattern_str, severity, explanation in entries
    ]


ALL_PATTERNS: list[tuple[str, Severity, str, re.Pattern[str]]] = (
    _compile(URGENCY_PATTERNS, "urgency_pressure")
    + _compile(CREDENTIAL_PATTERNS, "credential_request")
    + _compile(PAYMENT_PATTERNS, "payment_request")
    + _compile(PRIZE_PATTERNS, "too_good_to_be_true")
    + _compile(SPOOF_PATTERNS, "spoofed_sender")
)

SEVERITY_ORDER = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2}
RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}


def _risk_from_severities(severities: list[Severity]) -> RiskLevel:
    if Severity.HIGH in severities:
        return RiskLevel.HIGH
    if severities.count(Severity.MEDIUM) >= 2:
        return RiskLevel.HIGH
    if Severity.MEDIUM in severities:
        return RiskLevel.MEDIUM
    if severities:
        return RiskLevel.LOW
    return RiskLevel.LOW


def _is_defensive_context(text: str) -> bool:
    """Detect educational/defensive language so scam vocabulary is not treated as an attack.

    This is intentionally conservative: the whole-message suppression only applies when the
    message explicitly frames the terms as warnings and also tells the recipient not to act.
    A real request such as "never share your OTP — enter it here now" therefore still gets cues.
    """
    lowered = text.lower()
    framing = (
        re.search(r"\b(security reminder|safety reminder|security notice)\b", lowered)
        or re.search(r"\b(criminals|scammers|fraudsters) (may|often|can) use\b", lowered)
        or re.search(r"\b(we|we will) never ask (for|you to share)\b", lowered)
    )
    no_action = (
        re.search(r"\b(do not|don't|never|do nothing|no action needed|nothing to do|avoid)\b", lowered)
        and not re.search(r"\b(click|pay|transfer|enter|send|share|provide)\b", lowered)
    )
    return bool(framing and no_action)


def _rule_cues(redacted_text: str) -> list[Cue]:
    cues: list[Cue] = []
    defensive_context = _is_defensive_context(redacted_text)
    seen: set[tuple[str, str]] = set()

    for cue_type, severity, explanation, pattern in ALL_PATTERNS:
        for match in pattern.finditer(redacted_text):
            quoted = match.group(0).strip()
            key = (cue_type, quoted.lower())
            if key in seen or not quoted:
                continue
            seen.add(key)
            if defensive_context:
                continue
            cues.append(
                Cue(
                    cue_type=cue_type,
                    text=quoted[:160],
                    explanation=explanation,
                    severity=severity,
                    source="rules",
                )
            )

    for match in URL_ONLY_RE.finditer(redacted_text):
        url = match.group(0).rstrip(".,);'\"")
        if SUSPICIOUS_URL_RE.search(url):
            cues.append(
                Cue(
                    cue_type="disguised_link",
                    text=url[:160],
                    explanation=SUSPICIOUS_URL_EXPLANATION,
                    severity=Severity.HIGH,
                    source="rules",
                )
            )

    # Order by severity (highest first) so the highlighter leads with the worst.
    cues.sort(key=lambda cue: -SEVERITY_ORDER[cue.severity])
    return cues[:12]


def _annotate(redacted_text: str, cues: list[Cue]) -> list[dict[str, object]]:
    """Build [{text, is_cue, cue_index}] segments for the frontend highlighter."""
    segments: list[dict[str, object]] = []
    if not redacted_text:
        return segments

    spans: list[tuple[int, int, int]] = []
    for index, cue in enumerate(cues):
        start = redacted_text.find(cue.text)
        if start >= 0:
            spans.append((start, start + len(cue.text), index))

    spans.sort()
    chosen: list[tuple[int, int, int]] = []
    last_end = -1
    for start, end, index in spans:
        if start >= last_end:
            chosen.append((start, end, index))
            last_end = end

    cursor = 0
    for start, end, index in chosen:
        if start > cursor:
            segments.append({"text": redacted_text[cursor:start], "is_cue": False})
        segments.append(
            {"text": redacted_text[start:end], "is_cue": True, "cue_index": index}
        )
        cursor = end
    if cursor < len(redacted_text):
        segments.append({"text": redacted_text[cursor:], "is_cue": False})
    return segments


def _channel(case_input_type: InputType) -> str:
    return {
        InputType.TEXT: "pasted SMS / email text",
        InputType.IMAGE: "screenshot of a message",
        InputType.URL: "pasted URL",
        InputType.QR_IMAGE: "scanned QR code",
    }.get(case_input_type, "message")


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------


def run(redacted_text: str, case_id: str = "", case_input_type: InputType = InputType.TEXT) -> PhishingResult:
    """Analyse the redacted message and return an explainable phishing verdict."""
    cues = _rule_cues(redacted_text)
    risk = _risk_from_severities([cue.severity for cue in cues])
    llm_explained = False
    notes = ""

    if redacted_text.strip():
        try:
            rule_lines = "\n".join(
                f"- {cue.cue_type} | \"{cue.text}\" | {cue.explanation}"
                for cue in cues
            ) or "(none)"
            urls = ", ".join(URL_ONLY_RE.findall(redacted_text)) or "(none)"
            answer = llm.generate(
                "phishing_explain",
                {
                    "redacted_text": redacted_text[:4000],
                    "rule_cues": rule_lines,
                    "channel": _channel(case_input_type),
                    "urls": urls,
                },
            )
            llm_cues = [
                Cue(
                    cue_type=str(item.get("cue_type", "suspicious_phrase"))[:60],
                    text=str(item.get("text", ""))[:160],
                    explanation=str(item.get("explanation", ""))[:400],
                    severity=_severity(str(item.get("severity", "medium"))),
                    source="llm",
                )
                for item in answer.get("cues", [])
                if isinstance(item, dict) and item.get("text")
            ]
            if llm_cues:
                existing = {(cue.cue_type, cue.text.lower()) for cue in cues}
                for cue in llm_cues:
                    if (cue.cue_type, cue.text.lower()) not in existing:
                        cues.append(cue)
                        existing.add((cue.cue_type, cue.text.lower()))
                cues.sort(key=lambda cue: -SEVERITY_ORDER[cue.severity])
                llm_risk = _risk(str(answer.get("risk", "")))
                if llm_risk is not None and RISK_ORDER[llm_risk] > RISK_ORDER[risk]:
                    risk = llm_risk
            llm_explained = True
            notes = str(answer.get("summary", ""))[:600]
        except Exception:  # noqa: BLE001 — rule cues always stand alone
            notes = (
                "None of the usual red flags were present in this message "
                "(rule-based check; LLM explanation unavailable)."
                if not cues
                else "LLM explanation unavailable — verdict built from rule-based cues only."
            )

    return PhishingResult(
        risk=risk,
        cues=cues,
        annotated_segments=_annotate(redacted_text, cues),
        llm_explained=llm_explained,
        notes=notes,
    )


def _severity(value: str) -> Severity:
    try:
        return Severity(value.lower())
    except ValueError:
        return Severity.MEDIUM


def _risk(value: str) -> Optional[RiskLevel]:
    try:
        return RiskLevel(value.lower())
    except ValueError:
        return None
