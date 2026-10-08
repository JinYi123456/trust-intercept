"""Module 3 — Privacy-Preserving Scam Reporter.

Builds the downloadable, redacted report the user can forward to a bank,
telco, or CISA-style portal. TRUST//INTERCEPT prepares it; the human sends it.

Redaction is re-applied defensively here (the case text should already be
redacted) and the evidence hash is computed over the REDACTED text so the
bundle can be shared without leaking identifiers. The PII map with original
values never enters this module's output.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from backend.agent import llm
from backend.models.case import (
    Case,
    Cue,
    InputType,
    ReportBundle,
    Verdict,
)
from backend.tools.pii_redact import redact_pii

CHANNEL_NAMES = {
    InputType.TEXT: "Pasted SMS / email text",
    InputType.IMAGE: "Screenshot of a message (OCR)",
    InputType.URL: "Pasted URL",
    InputType.QR_IMAGE: "Scanned QR code",
}


def _evidence_hash(redacted_text: str) -> str:
    """SHA-256 over the redacted text — stable, shareable, leak-free."""
    return hashlib.sha256(redacted_text.encode("utf-8")).hexdigest()[:16]


def _summary_via_llm(redacted_text: str, cues: list[Cue], module_notes: str) -> str | None:
    try:
        answer = llm.generate(
            "report_summary",
            {
                "redacted_text": redacted_text[:4000],
                "cues": "\n".join(
                    f"- {cue.cue_type} | \"{cue.text}\" | {cue.severity.value}" for cue in cues
                )
                or "(none)",
                "module_notes": module_notes or "(none)",
            },
        )
        summary = str(answer.get("summary", "")).strip()
        return summary or None
    except Exception:  # noqa: BLE001 — the deterministic summary always works
        return None


def _summary_template(redacted_text: str, cues: list[Cue]) -> str:
    """Deterministic English summary used when no LLM is available."""
    if not cues:
        return (
            "A message was submitted for review. No scam cues were detected by the rule "
            "engine, so this report records the message for reference only."
        )
    top_types = sorted({cue.cue_type for cue in cues})
    cue_list = ", ".join(top_types)
    return (
        f"A message containing {len(cues)} detected red flag(s) — pattern(s): {cue_list} — "
        "was submitted for review. The message used pressure or deception tactics "
        "(quoted in the cues section below) and is reported so the receiving channel can "
        "investigate the source. The recipient did not act on the message before reporting."
    )


def _render_markdown(
    case: Case,
    verdict: Verdict | None,
    cues: list[Cue],
    summary: str,
    hash_value: str,
) -> str:
    generated = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    lines = [
        "# Fraud Report (prepared by TRUST//INTERCEPT)",
        "",
        f"**Prepared:** {generated}",
        f"**Case ID:** `{case.id}`",
        f"**Evidence hash (SHA-256, redacted text):** `{hash_value}`",
        "",
        "## 1. Incident summary",
        summary,
        "",
        "## 2. Channel & timing",
        f"- Channel: {CHANNEL_NAMES.get(case.input_type, case.input_type.value)}",
        f"- Reported at: {case.created_at.isoformat(timespec='seconds')}",
        "",
        "## 3. Redacted message",
        "```",
        case.redacted_text or "(no text content)",
        "```",
        "",
        "## 4. Detected cues",
    ]

    if cues:
        for index, cue in enumerate(cues, start=1):
            lines.append(
                f"{index}. **{cue.cue_type}** ({cue.severity.value} severity) — \"{cue.text}\" — "
                f"{cue.explanation}"
            )
    else:
        lines.append("No scam cues were detected by the rule engine.")

    lines += [
        "",
        "## 5. Risk assessment",
    ]
    if verdict is not None:
        lines += [
            f"- Risk score: **{verdict.score.value.upper()}** "
            f"(confidence: {verdict.confidence.value})",
        ]
        if verdict.uncertainty_note:
            lines.append(f"- Uncertainty: {verdict.uncertainty_note}")
    else:
        lines.append("- No synthesis verdict was recorded for this case.")
    lines += [
        "",
        "## 6. Links observed",
    ]
    urls = [line for line in (case.redacted_text or "").split() if line.startswith("http")]
    if urls:
        lines += [f"- {url}" for url in urls]
    else:
        lines.append("- None found in the message text.")

    lines += [
        "",
        "## 7. Where to report (Malaysia)",
        "The reporter chooses where to send this bundle. Nothing is transmitted automatically.",
        "Always navigate to these portals yourself — never through a link from the suspicious message:",
        "",
        "- **NSRC — National Scam Response Centre: call 997** (24/7 hotline for scam reports and fund-freeze requests; call immediately after any transfer).",
        "- **Semak Mule (PDRM): https://semakmule.rmp.gov.my** — check whether the account/phone number in the message is a known mule account.",
        "- **Bank Negara Malaysia (BNM): https://www.bnm.gov.my** — BNMTELELINK 1-300-88-5465 for banking/insurance-related complaints.",
        "- **CCID Online Reporting (PDRM): https://report.iccid.rmp.gov.my** — commercial crime investigation online report.",
        "",
        "## 8. Privacy notice",
        "Personal identifiers in the original message were replaced with placeholders",
        "(e.g. [REDACTED_IC_NRIC_1]) before this report was assembled. TRUST//INTERCEPT never",
        "uploads the unredacted original; the reporter chooses whether to attach it.",
        "",
        "---",
        "Prepared by TRUST//INTERCEPT (solo-sentinel demo). The reporter reviews and sends this",
        "report themselves; nothing is transmitted automatically.",
    ]
    return "\n".join(lines)


def run(case: Case, verdict: Verdict | None) -> ReportBundle:
    """Assemble the redacted report bundle for a case."""
    # Defensive re-redaction: never trust that upstream redaction is complete.
    redacted_text, _ = redact_pii(case.redacted_text or case.raw_text, use_ner=False)

    cues = list(verdict.cues) if verdict else []
    module_notes = (
        f"Risk score {verdict.score.value}; confidence {verdict.confidence.value}."
        if verdict
        else ""
    )

    summary = _summary_via_llm(redacted_text, cues, module_notes)
    if summary is None:
        summary = _summary_template(redacted_text, cues)

    hash_value = _evidence_hash(redacted_text)
    markdown = _render_markdown(case, verdict, cues, summary, hash_value)

    return ReportBundle(
        case_id=case.id,
        channel=CHANNEL_NAMES.get(case.input_type, case.input_type.value),
        incident_timestamp=case.created_at,
        cues_detected=cues,
        redacted_text=redacted_text,
        evidence_hash=hash_value,
        summary=summary,
        report_markdown=markdown,
    )
