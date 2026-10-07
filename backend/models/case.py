"""Pydantic data models for the TRUST//INTERCEPT pipeline.

The models encode the human-in-the-loop contract structurally:

* ``Verdict`` may *propose* an action (``action_required``) but carries **no**
  ``action_taken`` field — there is no code path from "module finishes" to
  "report sent" or "contact blocked".
* Only a ``Decision`` (written exclusively by ``routers/review.py`` after an
  explicit POST to ``/case/{id}/decision``) can record that something actually
  happened, and it freezes a snapshot of the verdict at approval time.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_case_id() -> str:
    return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InputType(str, Enum):
    TEXT = "text"           # pasted SMS / email body
    IMAGE = "image"         # screenshot of a message
    URL = "url"             # a bare pasted link
    QR_IMAGE = "qr_image"   # a picture containing a QR code
    AUDIO = "audio"         # suspicious voice call / voicemail (deepfake check)


class CaseStatus(str, Enum):
    RECEIVED = "received"
    NORMALISING = "normalising"
    INVESTIGATING = "investigating"
    AWAITING_REVIEW = "awaiting_review"
    CLOSED = "closed"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HumanAction(str, Enum):
    """The four gate actions a human can approve on the Review screen."""

    LOOKS_SAFE = "looks_safe"
    REPORT = "report"
    BLOCK_WARN = "block_warn"
    DISAGREE_RECHECK = "disagree_recheck"


# ---------------------------------------------------------------------------
# Evidence primitives
# ---------------------------------------------------------------------------


class PiiFinding(BaseModel):
    """One redacted item. ``original`` never leaves the user's session."""

    entity_type: Literal[
        "IC_NRIC", "SSN", "CREDIT_CARD", "OTP", "PHONE_NUMBER", "EMAIL", "PERSON"
    ]
    original: str
    placeholder: str          # e.g. "[REDACTED_IC_NRIC_1]"
    source: Literal["regex", "presidio", "spacy"] = "regex"


class Cue(BaseModel):
    """A specific, quoted, explained reason behind the verdict."""

    cue_type: str             # e.g. "urgency_pressure", "credential_request"
    text: str                 # exact quote from the (redacted) message
    explanation: str          # plain-language "why this is a red flag"
    severity: Severity = Severity.MEDIUM
    source: Literal["rules", "llm"] = "rules"


class Evidence(BaseModel):
    """Verbatim tool output kept for the explainability trace."""

    tool: str                 # e.g. "redirect_walker", "domain_lookup", "llm_synthesis"
    raw_output: dict[str, Any]
    collected_at: datetime = Field(default_factory=utcnow)


# ---------------------------------------------------------------------------
# Audio forensics primitives (voice scam / deepfake detection)
# ---------------------------------------------------------------------------


class AudioFinding(BaseModel):
    """One explainable audio red flag with its measured basis."""

    cue_type: str             # e.g. "robotic_artifact", "pitch_instability", "coercion_language"
    text: str                 # quote (transcript cue) or measurement description
    explanation: str          # plain-language "why this matters"
    severity: Severity = Severity.MEDIUM
    source: Literal["local_analysis", "llm"] = "local_analysis"


class AudioIntel(BaseModel):
    """Module output for AUDIO cases: local DSP pass + optional Gemini pass."""

    module: Literal["audio_forensics"] = "audio_forensics"
    filename: str = ""
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    format_ok: bool = False
    # Local offline DSP metrics (always computed, no network, no keys):
    local_pass: dict[str, Any] = {}
    local_risk: RiskLevel = RiskLevel.LOW
    # Gemini native-audio pass (free tier; skipped gracefully when unavailable):
    llm_pass: dict[str, Any] = {}
    llm_risk: RiskLevel = RiskLevel.LOW
    transcript_excerpt: str = ""   # redacted transcript text (cue quotes come from here)
    findings: list[AudioFinding] = []
    risk: RiskLevel = RiskLevel.LOW
    verdict_text: str = ""
    notes: list[str] = []


# ---------------------------------------------------------------------------
# Module 2 primitives: redirect chain + domain intel
# ---------------------------------------------------------------------------


class RedirectHop(BaseModel):
    index: int
    url: str
    status_code: Optional[int] = None
    location: str = ""
    note: str = ""


class RedirectChain(BaseModel):
    start_url: str
    final_url: str = ""
    hops: list[RedirectHop] = []
    loop_detected: bool = False
    truncated: bool = False
    error: str = ""


class ReputationEngineResult(BaseModel):
    engine: Literal["virustotal", "safe_browsing"]
    checked: bool = False
    malicious: bool = False
    detail: str = ""              # e.g. "4/93 vendors flagged this URL"
    unavailable_reason: str = ""  # why no verdict (no key, rate limit, no record...)


class DomainIntel(BaseModel):
    domain: str
    created_at: str = ""          # ISO date from WHOIS/RDAP, "" if unknown
    domain_age_days: Optional[int] = None
    registrar: str = ""
    lookup_source: Literal["whois", "rdap", ""] = ""
    reputation: list[ReputationEngineResult] = []
    cache_hit: bool = False
    notes: list[str] = []


# ---------------------------------------------------------------------------
# Module outputs
# ---------------------------------------------------------------------------


class PhishingResult(BaseModel):
    module: Literal["module_1_phishing"] = "module_1_phishing"
    risk: RiskLevel = RiskLevel.LOW
    cues: list[Cue] = []
    annotated_segments: list[dict[str, Any]] = []   # [{text, is_cue, cue_index}]
    llm_explained: bool = False
    notes: str = ""


class LinkSafetyResult(BaseModel):
    module: Literal["module_2_link_safety"] = "module_2_link_safety"
    risk: RiskLevel = RiskLevel.LOW
    urls: list[str] = []
    chains: list[RedirectChain] = []
    domains: list[DomainIntel] = []
    link_flags: list[Cue] = []
    verdict_text: str = ""
    llm_explained: bool = False
    notes: list[str] = []


class ReportBundle(BaseModel):
    """Module 3 output — a redacted, human-sent fraud report."""

    module: Literal["module_3_reporter"] = "module_3_reporter"
    case_id: str
    channel: str
    incident_timestamp: datetime
    cues_detected: list[Cue] = []
    redacted_text: str
    evidence_hash: str
    summary: str
    report_markdown: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = []
    correct_index: int = 0
    explanation: str = ""


class Quiz(BaseModel):
    """Module 4 output — the adaptive awareness mini-quiz."""

    module: Literal["module_4_coach"] = "module_4_coach"
    case_id: str
    pattern_name: str
    questions: list[QuizQuestion] = []
    generated_by_llm: bool = False


# ---------------------------------------------------------------------------
# The verdict — proposes, never acts
# ---------------------------------------------------------------------------


class Verdict(BaseModel):
    case_id: str
    score: RiskLevel
    cues: list[Cue] = []
    confidence: Confidence = Confidence.MEDIUM
    uncertainty_note: str = ""
    summary: str = ""
    action_required: bool = False
    reasoning_trace: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    # NOTE: deliberately NO `action_taken` field — see routers/review.py.


# ---------------------------------------------------------------------------
# The decision — the only record that an action actually happened
# ---------------------------------------------------------------------------


class DecisionRequest(BaseModel):
    human_action: HumanAction
    correction: str = ""       # required when human_action == disagree_recheck
    decided_by: str = "user"


class Decision(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    case_id: str
    human_action: HumanAction
    action_taken: str          # written ONLY by routers/review.py
    verdict_snapshot: Verdict  # frozen copy of the verdict at approval time
    correction: str = ""
    decided_by: str = "user"
    decided_at: datetime = Field(default_factory=utcnow)


# ---------------------------------------------------------------------------
# API payloads
# ---------------------------------------------------------------------------


class CaseCreate(BaseModel):
    input_type: InputType = InputType.TEXT
    text: str = ""
    url: str = ""
    image_b64: str = ""        # base64-encoded screenshot or QR image
    image_filename: str = ""
    audio_b64: str = ""        # base64-encoded voice call / voicemail (mp3/wav/m4a)
    audio_filename: str = ""
    request_modules: list[str] = []   # optional explicit module override


class Case(BaseModel):
    id: str = Field(default_factory=new_case_id)
    input_type: InputType
    raw_text: str = ""         # original input — NEVER persisted to SQLite
    redacted_text: str = ""    # PII-redacted copy used for all downstream reasoning
    url: str = ""
    image_filename: str = ""
    audio_filename: str = ""   # original audio file name; audio bytes never persisted
    request_modules: list[str] = []
    normalisation_notes: list[str] = []
    pii_map: list[PiiFinding] = []   # originals kept in-session only
    status: CaseStatus = CaseStatus.RECEIVED
    created_at: datetime = Field(default_factory=utcnow)


class CaseView(BaseModel):
    """Everything the Review screen needs, in one payload."""

    case: Case
    evidence: list[Evidence] = []
    verdict: Optional[Verdict] = None
    decisions: list[Decision] = []
    report: Optional[ReportBundle] = None
    quiz: Optional[Quiz] = None
