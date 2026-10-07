"""The Router — decides which module(s) a Case needs.

Lightweight classifier per the blueprint: quick regex signals first (contains
URL? contains 'OTP'/'urgent'? is an image?), then a small LLM triage call ONLY
when the regex finds nothing — so the cheap, deterministic path does most of
the work and the LLM is a tie-breaker.

Modules 1 (phishing) and 2 (link safety) are investigation modules and run
immediately. Modules 3 (report) and 4 (coach) are defensive actions — they are
listed as `deferred` and only execute after the human approves them on the
Review screen (the structural gate in routers/review.py).
"""
from __future__ import annotations

import re

from backend.agent import llm
from backend.models.case import Case

MODULE_1 = "module_1_phishing"
MODULE_2 = "module_2_link_safety"
MODULE_3 = "module_3_reporter"
MODULE_4 = "module_4_coach"

INVESTIGATION_MODULES = {MODULE_1, MODULE_2}
DEFERRED_MODULES = [MODULE_3, MODULE_4]

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
URGENCY_RE = re.compile(
    r"\b(urgent|urgently|immediately|act now|final (notice|warning)|expires? (today|soon)|"
    r"account (will be )?(suspended|closed|locked)|avoid (suspension|cancellation)|"
    r"parcel (is )?(held|on hold|pending)|last (warning|chance)|within \d+\s*(hours?|minutes?|days?))\b",
    re.IGNORECASE,
)
CREDENTIAL_RE = re.compile(
    r"\b(otp|one[- ]time (password|pin|code)|passcode|password|pin code|ic number|nric|"
    r"credit card|card (details|number)|cvv|bank account|internet banking|online banking|"
    r"verify your (account|identity)|confirm your (account|identity)|singpass)\b",
    re.IGNORECASE,
)
PAYMENT_RE = re.compile(
    r"\b(delivery fee|handling fee|customs (fee|charge|duty)|unpaid (fee|invoice|amount)|"
    r"release (fee|charge)|transfer (of )?\$?\d+|pay \$?\d+|payment of \$?\d+)\b",
    re.IGNORECASE,
)
PRIZE_RE = re.compile(
    r"\b(congratulations|you (have )?won|winner|lottery|prize|lucky draw|gift (card|voucher)|"
    r"cashback|rebate|refund)\b",
    re.IGNORECASE,
)


def _llm_triage(redacted_text: str) -> tuple[list[str], bool]:
    """Small LLM call used only when regex found no signals. Returns (modules, used)."""
    try:
        answer = llm.generate("router_triage", {"redacted_text": redacted_text[:2500]})
        modules: list[str] = []
        if answer.get("phishing_suspected") is True:
            modules.append(MODULE_1)
        if answer.get("link_suspected") is True:
            modules.append(MODULE_2)
        return modules, True
    except Exception:  # noqa: BLE001 — regex-only routing still covers the case
        return [], False


def route_case(case: Case) -> "RoutingPlan":
    signals: list[str] = []
    modules: list[str] = []
    used_llm = False

    text = case.redacted_text or ""
    has_url = bool(case.url) or bool(URL_RE.search(text))

    if has_url:
        modules.append(MODULE_2)
        signals.append("contains_url")

    if URGENCY_RE.search(text):
        signals.append("urgency_language")
    if CREDENTIAL_RE.search(text):
        signals.append("credential_or_otp_request")
    if PAYMENT_RE.search(text):
        signals.append("payment_request")
    if PRIZE_RE.search(text):
        signals.append("too_good_to_be_true")

    # Any message text is worth a phishing pass when other signals exist, or
    # when the user explicitly submitted it for review.
    if text.strip() and (signals or not has_url):
        modules.append(MODULE_1)
        if not signals:
            signals.append("no_regex_signals_forwarded_to_module_1")

    # Ambiguous case: regex found nothing at all -> one small LLM triage call.
    if not signals and text.strip():
        triage_modules, used_llm = _llm_triage(text)
        for module in triage_modules:
            if module not in modules:
                modules.append(module)
        signals.append("llm_triage" if used_llm else "llm_unavailable_defaulted_to_module_1")
        if MODULE_1 not in modules and not has_url:
            # LLM unavailable or saw nothing — still give the text a rule-based pass.
            modules.append(MODULE_1)

    # Explicit module requests from the intake form override the plan.
    for requested in case.request_modules:
        if requested in INVESTIGATION_MODULES and requested not in modules:
            modules.append(requested)
            signals.append(f"requested:{requested}")

    return RoutingPlan(
        modules=modules,
        deferred_modules=list(DEFERRED_MODULES),
        signals=signals,
        used_llm=used_llm,
    )


class RoutingPlan:
    """Attributes are set as plain attributes; persisted via model_dump-like dict."""

    def __init__(self, modules: list[str], deferred_modules: list[str], signals: list[str], used_llm: bool):
        self.modules = modules
        self.deferred_modules = deferred_modules
        self.signals = signals
        self.used_llm = used_llm

    def model_dump(self, mode: str = "python") -> dict:
        return {
            "modules": self.modules,
            "deferred_modules": self.deferred_modules,
            "signals": self.signals,
            "used_llm": self.used_llm,
        }
