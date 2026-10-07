"""PII redaction — runs BEFORE any text reaches an external LLM or API.

``redact_pii`` returns ``(redacted_text, pii_map)``:

* ``redacted_text`` — the message with every IC/NRIC, SSN, credit card
  (Luhn-validated), one-time passcode (OTP), e-mail address and phone number
  replaced by a placeholder token such as ``[REDACTED_CREDIT_CARD_1]``.
* ``pii_map`` — the list of :class:`PiiFinding` linking each placeholder back
  to its original value. The map (and therefore the originals) **never leaves
  the caller's session**: the database persists only the redacted copy.

Engine priority: regex first (deterministic, no dependencies), then NER via
Microsoft Presidio when installed, falling back to spaCy ``PERSON`` entities.
The redactor is deliberately biased toward over-redaction — a false positive
costs nothing; a missed IC number costs privacy.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from backend.models.case import PiiFinding

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Singapore-style IC/NRIC: letter + 7 digits + checksum letter (S/T/F/G).
NRIC_RE = re.compile(r"\b([STFG]\s?\d{7}\s?[A-Z])\b", re.IGNORECASE)

# US Social Security Number: 123-45-6789.
SSN_RE = re.compile(r"\b(\d{3}-\d{2}-\d{4})\b")

# One-time passcode (OTP): 4-8 digit codes anchored to a keyword —
# "OTP 884213", "Your code is 884213", "884213 is your Singpass OTP",
# "G-5591 is your Google verification code". Only the DIGITS are replaced so
# the keyword itself survives and downstream credential-request cue detection
# still fires on the redacted copy. The generic phone pass requires 8+ digits
# and would otherwise leave 6-digit codes behind.
OTP_FORWARD_RE = re.compile(
    r"(?P<head>\b(?:otp|one[- ]time (?:password|pin|passcode)|passcode|password|pin|"
    r"verification code|security code|code)\b\D{0,12}?)(?P<code>\d{4,8})(?!\d)",
    re.IGNORECASE,
)

# Reversed phrasing: the code comes BEFORE the keyword, connected by short
# letter-only filler ("884213 is your Singpass OTP"). Bare "code" is too
# generic for this direction and is deliberately excluded.
OTP_REVERSED_RE = re.compile(
    r"(?P<code>(?<!\d)\d{4,8})(?!\d)"
    r"\s*(?:is\s+|:)?\s*(?:your\s+)?(?:[A-Za-z]{1,12}\s+){0,2}"
    r"\b(?:otp|one[- ]time (?:password|pin|passcode)|passcode|password|pin|"
    r"verification code|security code)\b",
    re.IGNORECASE,
)

# Credit card: 13-19 digits, optionally separated by single spaces or dashes.
# Validated with the Luhn checksum to avoid redacting order numbers.
CARD_RE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# Phone: 8+ digits with optional +country code and single separators. This
# intentionally also catches dates written like 20-09-2026 — over-redaction
# is the safe failure mode.
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s\-()]{6,16}\d)(?!\d)")

# Presidio entity label -> our PiiFinding entity_type. Labels not listed are skipped.
_PRESIDIO_LABELS = {
    "PERSON": "PERSON",
    "PHONE_NUMBER": "PHONE_NUMBER",
    "CREDIT_CARD": "CREDIT_CARD",
    "EMAIL_ADDRESS": "EMAIL",
    "US_SSN": "SSN",
    "SG_NRIC_FIN": "IC_NRIC",  # supported by recent Presidio versions
}

_NER_CACHE: dict[str, object] = {}


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def _luhn_ok(digits: str) -> bool:
    total = 0
    alt = False
    for ch in reversed(digits):
        value = ord(ch) - 48
        if alt:
            value *= 2
            if value > 9:
                value -= 9
        total += value
        alt = not alt
    return total % 10 == 0


def _card_validator(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    if not 13 <= len(digits) <= 19:
        return False
    return _luhn_ok(digits)


def _extends_number_run(text: str, start: int, end: int) -> bool:
    """True when the matched digits continue a longer (8+ digit) number.

    Scans across single spaces/dashes/brackets only, so ``9123 4567`` is one
    phone number while ``attempt 5, OTP 884213`` is not — such runs are left
    for the generic card/phone passes, which redact them anyway.
    """
    total = end - start

    def scan(indices):
        nonlocal total
        gaps = 0
        for i in indices:
            ch = text[i]
            if ch.isdigit():
                total += 1
                gaps = 0
            elif ch in " -()" and gaps < 2:
                gaps += 1
            else:
                break

    scan(range(start - 1, -1, -1))
    scan(range(end, len(text)))
    return total >= 8


# ---------------------------------------------------------------------------
# Regex redactor
# ---------------------------------------------------------------------------


class _Redactor:
    def __init__(self) -> None:
        self.findings: list[PiiFinding] = []
        self.counters: dict[str, int] = {}

    def _placeholder(self, entity_type: str) -> str:
        self.counters[entity_type] = self.counters.get(entity_type, 0) + 1
        return f"[REDACTED_{entity_type}_{self.counters[entity_type]}]"

    def _apply(
        self,
        text: str,
        pattern: "re.Pattern[str]",
        entity_type: str,
        validator: Optional[Callable[[str], bool]] = None,
    ) -> str:
        def replace(match: "re.Match[str]") -> str:
            original = match.group(0)
            if validator is not None and not validator(original):
                return original
            placeholder = self._placeholder(entity_type)
            self.findings.append(
                PiiFinding(
                    entity_type=entity_type,  # type: ignore[arg-type]
                    original=original,
                    placeholder=placeholder,
                    source="regex",
                )
            )
            return placeholder

        return pattern.sub(replace, text)

    def _merge_external(
        self,
        current_text: str,
        candidates: list[tuple[str, str, str]],
    ) -> str:
        """Merge NER findings (entity_type, original, source) by literal replace."""
        for entity_type, original, source in candidates:
            if not original or original not in current_text:
                continue  # already redacted by a regex pass, or whitespace shifted
            placeholder = self._placeholder(entity_type)
            current_text = current_text.replace(original, placeholder, 1)
            self.findings.append(
                PiiFinding(
                    entity_type=entity_type,  # type: ignore[arg-type]
                    original=original,
                    placeholder=placeholder,
                    source=source,  # type: ignore[arg-type]
                )
            )
        return current_text


def _apply_otp(text: str, redactor: _Redactor) -> str:
    """Redact one-time passcodes while KEEPING the anchoring keyword.

    Replacing only the digits (not the word "OTP" itself) preserves the
    credential-request cues that downstream phishing detection relies on.
    Codes that are part of a longer 8+ digit run (phone numbers) are skipped
    and handled by the generic phone pass instead.
    """

    def _record(code: str) -> str:
        placeholder = redactor._placeholder("OTP")
        redactor.findings.append(
            PiiFinding(
                entity_type="OTP",
                original=code,
                placeholder=placeholder,
                source="regex",
            )
        )
        return placeholder

    def replace_reversed(match: "re.Match[str]") -> str:
        code = match.group("code")
        if _extends_number_run(text, match.start("code"), match.end("code")):
            return match.group(0)
        return _record(code) + match.group(0)[len(code) :]

    def replace_forward(match: "re.Match[str]") -> str:
        code = match.group("code")
        if _extends_number_run(text, match.start("code"), match.end("code")):
            return match.group(0)
        return match.group("head") + _record(code)

    result = OTP_REVERSED_RE.sub(replace_reversed, text)
    return OTP_FORWARD_RE.sub(replace_forward, result)


# ---------------------------------------------------------------------------
# Optional NER backends
# ---------------------------------------------------------------------------


def _presidio_candidates(text: str) -> list[tuple[str, str, str]]:
    """Return [(entity_type, original_text, 'presidio')] using Presidio, if installed."""
    if "presidio" in _NER_CACHE:
        analyzer = _NER_CACHE["presidio"]
        if analyzer is None:
            return []
    else:
        try:
            from presidio_analyzer import AnalyzerEngine  # type: ignore

            analyzer = AnalyzerEngine()
            _NER_CACHE["presidio"] = analyzer
        except Exception:  # ImportError, model download failures, NLTK issues...
            _NER_CACHE["presidio"] = None
            return []

    try:
        results = analyzer.analyze(  # type: ignore[union-attr]
            text=text,
            language="en",
            entities=list(_PRESIDIO_LABELS.keys()),
        )
    except Exception:
        return []

    candidates: list[tuple[str, str, str]] = []
    for result in results:
        label = _PRESIDIO_LABELS.get(result.entity_type)
        if label is None:
            continue
        original = text[result.start : result.end].strip()
        if original:
            candidates.append((label, original, "presidio"))
    return candidates


def _spacy_candidates(text: str) -> list[tuple[str, str, str]]:
    """Fallback NER: spaCy PERSON entities, if the model is installed."""
    if "spacy" in _NER_CACHE:
        nlp = _NER_CACHE["spacy"]
        if nlp is None:
            return []
    else:
        try:
            import spacy  # type: ignore

            nlp = spacy.load("en_core_web_sm")
            _NER_CACHE["spacy"] = nlp
        except Exception:  # ImportError or missing en_core_web_sm model
            _NER_CACHE["spacy"] = None
            return []

    try:
        doc = nlp(text)  # type: ignore[union-attr]
    except Exception:
        return []

    return [
        ("PERSON", entity.text.strip(), "spacy")
        for entity in doc.ents
        if entity.label_ == "PERSON" and entity.text.strip()
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def redact_pii(text: str, use_ner: bool = True) -> tuple[str, list[PiiFinding]]:
    """Redact PII from ``text`` and return ``(redacted_text, pii_map)``.

    The returned ``pii_map`` contains the original values and must stay in the
    user's session; never persist or transmit it.
    """
    if not text:
        return "", []

    redactor = _Redactor()
    result = text

    # Order matters: specific patterns first, generic digit runs last. OTP
    # runs after the card pass (so card fragments are never broken up) but
    # before the phone pass, which requires 8+ digits and would otherwise
    # leave 4-7 digit one-time codes behind.
    result = redactor._apply(result, NRIC_RE, "IC_NRIC")
    result = redactor._apply(result, SSN_RE, "SSN")
    result = redactor._apply(result, CARD_RE, "CREDIT_CARD", validator=_card_validator)
    result = _apply_otp(result, redactor)
    result = redactor._apply(result, EMAIL_RE, "EMAIL")
    result = redactor._apply(result, PHONE_RE, "PHONE_NUMBER")

    if use_ner:
        candidates = _presidio_candidates(text) or _spacy_candidates(text)
        result = redactor._merge_external(result, candidates)

    return result, redactor.findings


def contains_high_risk_pii(text: str) -> bool:
    """Cheap helper: does the raw text contain IC/NRIC, SSN or valid card patterns?"""
    if NRIC_RE.search(text) or SSN_RE.search(text):
        return True
    return any(_card_validator(match.group(0)) for match in CARD_RE.finditer(text))
