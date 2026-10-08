"""Module 4 — Adaptive Awareness Coach.

Turns the pattern detected in a real case into a short 3–4 question
interactive simulation with immediate feedback. The LLM generates the quiz
from the case's own cues; a deterministic English fallback keeps the demo
alive offline. This is a reinforcement aid, not a certified curriculum.
"""
from __future__ import annotations

from backend.agent import llm
from backend.models.case import Case, Quiz, QuizQuestion, Verdict


# ---------------------------------------------------------------------------
# Pattern naming
# ---------------------------------------------------------------------------

PATTERN_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Fake courier / parcel-fee scam", ("parcel", "delivery", "courier", "customs", "depot", "shipment", "pos laju", "poslaju", "j&t", "jt express", "ninja van")),
    ("Fake bank security alert", ("bank", "account suspended", "unusual activity", "compromised", "internet banking")),
    ("Fake OTP / verification-code request", ("otp", "one-time password", "verification code", "passcode")),
    ("Phishing 'verify your account' lure", ("verify your account", "confirm your identity", "update your details", "reactivate")),
    ("Prize / lottery / refund scam", ("congratulations", "you have won", "lottery", "prize", "refund", "cashback")),
    ("Government / tax authority impersonation", ("iras", "lhdn", "inland revenue", "tax authority", "police")),
    ("Macau scam — fake police/court call", ("macau", "criminal case", "money laundering", "arrest warrant", "interpol", "pdrm", "mahkamah", "court case", "embassy")),
    ("E-wallet freeze / KYC scam (TNG/Boost/ShopeePay)", ("touch 'n go", "touch n go", "tng", "boost", "grabpay", "shopeepay", "e-wallet", "ewallet")),
]


def _pattern_name(case: Case, verdict: Verdict | None) -> str:
    if verdict and verdict.cues:
        types = {cue.cue_type for cue in verdict.cues}
        if "payment_request" in types and "suspicious_link" in types:
            return "Fake courier / parcel-fee scam"
        if "credential_request" in types and "urgency_pressure" in types:
            return "Phishing 'verify your account' lure"
        if "credential_request" in types:
            return "Fake OTP / verification-code request"
        if "too_good_to_be_true" in types:
            return "Prize / lottery / refund scam"
        if "spoofed_sender" in types:
            return "Fake bank security alert"
        return "Urgency-pressure phishing message"

    haystack = f"{case.redacted_text} {case.url}".lower()
    for name, keywords in PATTERN_RULES:
        if any(keyword in haystack for keyword in keywords):
            return name
    return "Generic suspicious message"


# ---------------------------------------------------------------------------
# Deterministic fallback quiz
# ---------------------------------------------------------------------------

def _fallback_quiz(pattern_name: str, case_summary: str) -> list[QuizQuestion]:
    return [
        QuizQuestion(
            question=(
                f"You receive a message matching the pattern '{pattern_name}'. "
                "What is the SAFEST first reaction?"
            ),
            options=[
                "Pause — do not click anything and verify through an official channel you find yourself",
                "Click the link quickly before the deadline it mentions",
                "Reply to the sender asking if the message is real",
                "Forward it to friends so they can check it",
            ],
            correct_index=0,
            explanation=(
                "Scam messages manufacture urgency to stop you from verifying. Pausing and "
                "checking through a channel YOU choose (official app, published hotline) "
                "breaks the scam's core mechanism."
            ),
        ),
        QuizQuestion(
            question="Which detail in a message is the strongest red flag?",
            options=[
                "It mentions a delivery or parcel",
                "It asks you to enter credentials, an OTP, or card details on a linked page",
                "It uses your first name",
                "It arrives outside office hours",
            ],
            correct_index=1,
            explanation=(
                "No legitimate organisation asks for passwords, OTPs, or full card details "
                "via a message link. Any credential request is the clearest signal to stop."
            ),
        ),
        QuizQuestion(
            question="How should you check whether a link in a message is genuine?",
            options=[
                "Trust it if the message text looks professional",
                "Tap and hold (or hover) to preview the real destination and check the domain yourself",
                "Click it, then close the page quickly if it looks wrong",
                "Scan any QR code it contains with your camera app",
            ],
            correct_index=1,
            explanation=(
                "Previewing reveals the true destination before you commit. Opening the page "
                "even briefly can trigger drive-by downloads or leak your click-through data."
            ),
        ),
        QuizQuestion(
            question="After realising you interacted with a scam message, what should you do?",
            options=[
                "Delete the message and hope for the best",
                "Report it to your bank/telco and the national reporting portal, and change affected passwords",
                "Wait to see if money disappears from your account",
                "Confront the sender directly",
            ],
            correct_index=1,
            explanation=(
                "Fast reporting gives banks and telcos the best chance to block the scam "
                "infrastructure and recover funds — that is exactly the report bundle TRUST//INTERCEPT "
                "prepares for you."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# LLM-generated quiz
# ---------------------------------------------------------------------------

def _quiz_via_llm(pattern_name: str, case_summary: str, cues: list) -> list[QuizQuestion] | None:
    try:
        answer = llm.generate(
            "coach_quiz",
            {
                "pattern_name": pattern_name,
                "case_summary": case_summary[:1500],
                "cues": "\n".join(
                    f"- {cue.cue_type} | \"{cue.text}\" | {cue.explanation}" for cue in cues
                )
                or "(none)",
            },
        )
        questions = [
            QuizQuestion(
                question=str(item.get("question", ""))[:300],
                options=[str(option)[:200] for option in item.get("options", [])][:4],
                correct_index=int(item.get("correct_index", 0)),
                explanation=str(item.get("explanation", ""))[:500],
            )
            for item in answer.get("questions", [])
            if isinstance(item, dict) and item.get("question") and len(item.get("options", [])) >= 2
        ]
        questions = [q for q in questions if 0 <= q.correct_index < len(q.options)]
        return questions[:4] if len(questions) >= 3 else None
    except Exception:  # noqa: BLE001 — the fallback quiz always works
        return None


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------

def run(case: Case, verdict: Verdict | None) -> Quiz:
    pattern_name = _pattern_name(case, verdict)
    cues = verdict.cues if verdict else []
    case_summary = (
        verdict.summary
        or (case.redacted_text[:400] if case.redacted_text else case.url)
        or "A suspicious message was reviewed."
    )

    questions = _quiz_via_llm(pattern_name, case_summary, cues)
    generated_by_llm = questions is not None
    if questions is None:
        questions = _fallback_quiz(pattern_name, case_summary)

    return Quiz(
        case_id=case.id,
        pattern_name=pattern_name,
        questions=questions,
        generated_by_llm=generated_by_llm,
    )


FOCUS_BY_PATTERN = {
    "Fake courier / parcel-fee scam": "independent delivery verification + payment pressure",
    "Fake bank security alert": "official-channel verification + credential protection",
    "Fake OTP / verification-code request": "OTP secrecy + account takeover prevention",
    "Phishing 'verify your account' lure": "independent verification + suspicious-link avoidance",
    "Prize / lottery / refund scam": "unexpected reward skepticism + fee-before-payout detection",
    "Government / tax authority impersonation": "authority impersonation + independently sourced contact details",
}

def focus_for_question(pattern_name: str, question: QuizQuestion) -> str:
    text = f"{question.question} {question.explanation}".lower()
    if "otp" in text or "passcode" in text or "credential" in text:
        return "credential and OTP protection"
    if "link" in text or "url" in text or "click" in text:
        return "safe link verification"
    if "urgency" in text or "deadline" in text or "hurry" in text:
        return "urgency resistance"
    if "official" in text or "verify" in text or "channel" in text:
        return "independent verification"
    return FOCUS_BY_PATTERN.get(pattern_name, "evidence-based scam recognition")
