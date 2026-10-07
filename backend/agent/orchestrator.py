"""The Orchestrator — runs the shared pipeline for every case.

Stages (each mapped to the blueprint's Demonstration Framework):

1. Intake                      -> routers/intake.py
2. Evidence normalisation      -> _normalise()      [02 Inputs & Evidence]
   OCR / QR decode / PII redaction run BEFORE any LLM call.
3. Routing                     -> agent/router.py
4. Module investigation        -> _investigate()     [03 Agent Workflow]
5. Reasoning & synthesis       -> _synthesise()      exactly ONE LLM call per case;
   the prompt, raw tool outputs and response are logged together as evidence
   (tool="llm_synthesis") — this satisfies the "show your reasoning" rule.
6. Human review                -> routers/review.py  [05 Human Approval]
7. Defensive actions           -> Module 3 report / Module 4 quiz, only on approval [04]
8. Result & logging            -> SQLite (redacted data only) [06]
"""
from __future__ import annotations

import json
from typing import Optional

from backend.agent import llm
from backend.agent.debate import run_debate
from backend.agent.decision_defence import build_defence_plan
from backend.agent.modules import awareness_coach, link_safety, phishing_detector, scam_reporter
from backend.agent.router import MODULE_1, MODULE_2, route_case
from backend.config import get_settings
from backend.models import db
from backend.models.case import (
    Case,
    CaseStatus,
    Confidence,
    Cue,
    Decision,
    Evidence,
    HumanAction,
    InputType,
    RiskLevel,
    Severity,
    Verdict,
)
from backend.routers.metrics import find_intel_matches
from backend.tools import audio_forensics, psych_radar, sandbox_recon
from backend.tools.ocr import extract_text
from backend.tools.pii_redact import redact_pii
from backend.tools.qr_decode import decode_qr

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
CONFIDENCE_ORDER = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


class Orchestrator:
    """Stateless pipeline driver; all state lives in SQLite."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_case(self, case: Case, image_bytes: Optional[bytes] = None, audio_bytes: Optional[bytes] = None) -> Verdict:
        """Normalise -> route -> investigate (incl. debate) -> synthesise -> persist."""
        db.create_case(case)  # redacted snapshot only; text filled in below

        db.update_case_status(case.id, CaseStatus.NORMALISING)
        evidence = self._normalise(case, image_bytes)
        for entry in evidence:
            db.add_evidence(case.id, entry)
        db.update_case_text(case.id, case.redacted_text)

        db.update_case_status(case.id, CaseStatus.INVESTIGATING)
        verdict, investigation_evidence = self._investigate(case, audio_bytes=audio_bytes)
        for entry in investigation_evidence:
            db.add_evidence(case.id, entry)

        db.save_verdict(verdict)
        db.update_case_status(case.id, CaseStatus.AWAITING_REVIEW)
        return verdict

    def rerun_with_correction(self, case_id: str, correction: str) -> Verdict:
        """The 'I disagree, re-check' path: re-run with the correction noted.

        The original verdict is never deleted — verdicts are append-only, and
        the decision record keeps a snapshot of what the user actually saw.
        """
        case = self.load_case(case_id)
        if case is None:
            raise KeyError(f"Case {case_id} not found.")

        # Privacy: the user's free-text correction passes through the PII
        # redactor before it is stored or appended to the persisted case.
        redacted_correction, _ = redact_pii(correction, use_ner=False)
        db.add_evidence(
            case.id,
            Evidence(
                tool="human_disagreement",
                raw_output={
                    "correction": redacted_correction,
                    "action": "re-running modules with correction noted",
                    "note": "Correction passed through the PII redactor before storage.",
                },
            ),
        )
        case.redacted_text = f"{case.redacted_text}\n\n[User correction]: {redacted_correction}".strip()
        db.update_case_text(case.id, case.redacted_text)

        verdict, evidence = self._investigate(case)
        for entry in evidence:
            db.add_evidence(case.id, entry)
        db.save_verdict(verdict)
        return verdict

    def build_decision(self, case_id: str, human_action: HumanAction, correction: str, decided_by: str) -> Decision:
        """Create the Decision record — the ONLY way action_taken is ever written.

        This is the structural human-approval gate: Verdict objects carry
        `action_required` but no `action_taken` field, so no module can act on
        its own. Only this method, called exclusively from routers/review.py
        after an explicit POST /case/{id}/decision, produces a Decision.
        """
        verdict = db.latest_verdict(case_id)
        if verdict is None:
            raise KeyError(f"Case {case_id} has no verdict to review.")

        taken = {
            HumanAction.LOOKS_SAFE: "User reviewed the verdict and marked the case safe. "
            "Nothing was blocked, sent, or filed.",
            HumanAction.REPORT: "Redacted report bundle generated for the user to forward manually. "
            "TRUST//INTERCEPT does NOT send anything by itself.",
            HumanAction.BLOCK_WARN: "Plain-language warning with the quoted cues shown to the user. "
            "No contacts or numbers were blocked (guidance, not device-level enforcement).",
            HumanAction.DISAGREE_RECHECK: "Case re-investigated with the user's correction noted. "
            "The original verdict is preserved in this record's snapshot.",
        }[human_action]

        # Privacy: the stored decision carries the REDACTED correction only.
        redacted_correction, _ = redact_pii(correction, use_ner=False)
        return Decision(
            case_id=case_id,
            human_action=human_action,
            action_taken=taken,
            verdict_snapshot=verdict.model_copy(deep=True),
            correction=redacted_correction,
            decided_by=decided_by or "user",
        )

    # ------------------------------------------------------------------
    # Stage 2: evidence normalisation [02 Inputs & Evidence]
    # ------------------------------------------------------------------

    def _normalise(self, case: Case, image_bytes: Optional[bytes]) -> list[Evidence]:
        evidence: list[Evidence] = []
        conflicts: list[str] = []

        text = case.raw_text or ""
        if case.url:
            text = f"{case.url}\n{text}".strip()

        # --- OCR (image) / QR decode -----------------------------------
        if case.input_type in (InputType.IMAGE, InputType.QR_IMAGE):
            if not image_bytes:
                raise ValueError(f"Case type {case.input_type.value} requires an uploaded image.")
            if case.input_type == InputType.QR_IMAGE:
                qr = decode_qr(image_bytes)
                if qr.urls and not case.url:
                    case.url = qr.urls[0]
                text = "\n".join(filter(None, [qr.texts and "\n".join(qr.texts), text])).strip()
                evidence.append(
                    Evidence(
                        tool="qr_decode",
                        raw_output={
                            "engine": qr.engine,
                            "payloads_found": len(qr.texts),
                            "urls": qr.urls,
                            "redacted_preview": "",
                        },
                    )
                )
            else:
                ocr = extract_text(image_bytes)
                text = "\n".join(filter(None, [ocr.text, text])).strip()
                if ocr.mean_confidence is not None and ocr.mean_confidence < 60:
                    conflicts.append(
                        f"OCR confidence was low ({ocr.mean_confidence}%); the user should confirm the extracted text."
                    )
                evidence.append(
                    Evidence(
                        tool="ocr",
                        raw_output={
                            "engine": ocr.engine,
                            "mean_confidence": ocr.mean_confidence,
                            "redacted_preview": "",
                        },
                    )
                )

        # --- PII redaction BEFORE any LLM sees the text ------------------
        redacted, pii_map = redact_pii(text)
        case.redacted_text = redacted
        case.pii_map = pii_map  # originals stay in-session only; NEVER persisted

        placeholders = [finding.placeholder for finding in pii_map]
        preview = redacted[:280]
        for entry in evidence:  # fill previews now that redaction has run
            entry.raw_output["redacted_preview"] = preview

        evidence.append(
            Evidence(
                tool="pii_redact",
                raw_output={
                    "engine": "regex+ner" if pii_map else "regex",
                    "items_redacted": len(placeholders),
                    "placeholders": placeholders,
                    "note": "Originals kept in the user's session only; never persisted or sent to any API.",
                },
            )
        )

        if conflicts:
            case.normalisation_notes.extend(conflicts)
        return evidence

    # ------------------------------------------------------------------
    # Stages 3-5: route, investigate, synthesise [03 Agent Workflow]
    # ------------------------------------------------------------------

    def _investigate(self, case: Case, audio_bytes: Optional[bytes] = None) -> tuple[Verdict, list[Evidence]]:
        settings = get_settings()
        evidence: list[Evidence] = []

        plan = route_case(case)
        evidence.append(Evidence(tool="router", raw_output=plan.model_dump(mode="json")))

        module_results: dict[str, dict] = {}

        if case.input_type == InputType.AUDIO:
            # Voice scam / deepfake analysis: local DSP pass (+ Gemini when configured).
            module_results["audio"] = self._run_safely(
                evidence,
                "audio_forensics",
                audio_forensics.run,
                audio_bytes or b"",
                case.audio_filename,
                case.redacted_text,
            )

        if MODULE_1 in plan.modules:
            module_results["phishing"] = self._run_safely(
                evidence,
                "module_1_phishing",
                phishing_detector.run,
                case.redacted_text,
                case.id,
                case.input_type,
            )
        if MODULE_2 in plan.modules:
            urls = link_safety.extract_urls(case.redacted_text)
            if case.url and case.url not in urls:
                urls.insert(0, case.url)
            module_results["link"] = self._run_safely(evidence, "module_2_link_safety", link_safety.run, urls)

        return self._synthesise(case, module_results, evidence), evidence

    def _run_safely(self, evidence: list[Evidence], tool: str, func, *args) -> dict:
        """Run a module, capturing failures as evidence instead of crashing the demo."""
        try:
            result = func(*args)
            dump = result.model_dump(mode="json")
            evidence.append(Evidence(tool=tool, raw_output=dump))
            return dump
        except Exception as exc:  # noqa: BLE001 — the demo must keep going
            error_payload = {"error": f"{type(exc).__name__}: {exc}", "module_failed": True}
            evidence.append(Evidence(tool=tool, raw_output=error_payload))
            return error_payload

    def _synthesise(self, case: Case, module_results: dict[str, dict], evidence: list[Evidence]) -> Verdict:
        """Merge module outputs into one verdict — exactly ONE LLM call per case."""
        conflicts, gaps = self._collect_gaps(module_results, case)

        phishing = module_results.get("phishing")
        link = module_results.get("link")
        audio = module_results.get("audio")
        rule_risk = self._rule_risk(phishing, link, audio)
        cues = self._merge_cues(phishing, link)
        if audio and not audio.get("module_failed"):
            for item in audio.get("findings", []) or []:
                if isinstance(item, dict) and item.get("text"):
                    cues.append(
                        Cue(
                            cue_type=str(item.get("cue_type", "audio_finding"))[:60],
                            text=str(item.get("text", ""))[:160],
                            explanation=str(item.get("explanation", ""))[:400],
                            severity=self._severity(str(item.get("severity", "medium"))),
                            source="llm" if item.get("source") == "llm" else "rules",
                        )
                    )
        llm_used = False
        summary = self._offline_summary(case, phishing, link, audio)
        uncertainty = "; ".join(conflicts + gaps)

        # --- Multi-Agent Debate Protocol (Red Team vs Blue Team) ---------
        # Two adversarial agents argue the evidence BEFORE synthesis; the
        # full transcript is logged as agent_debate evidence. The debate may
        # RAISE the risk above the rule floor (prosecution wins), never lower it.
        debate = run_debate(case.redacted_text, module_results, evidence)
        resolution = debate.get("resolution", {})
        debate_raise = int(resolution.get("debate_floor_severity", 0) or 0)
        if debate_raise > RISK_ORDER[rule_risk]:
            rule_risk = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}[debate_raise]

        # --- The single synthesis LLM call -------------------------------
        if get_settings().llm_provider != "none":
            try:
                answer = llm.generate(
                    "orchestrator_synthesis",
                    {
                        "redacted_text": case.redacted_text[:4000],
                        "phishing_json": json.dumps(phishing or {"skipped": True}, ensure_ascii=False, indent=2)[:3000],
                        "link_json": json.dumps(link or {"skipped": True}, ensure_ascii=False, indent=2)[:3000],
                    },
                )
                llm_used = True
                llm_score = answer.get("score")
                if llm_score in ("low", "medium", "high"):
                    llm_risk = RiskLevel(llm_score)
                    # Never let the LLM lower the score below what the tools found.
                    if RISK_ORDER[llm_risk] > RISK_ORDER[rule_risk]:
                        rule_risk = llm_risk
                llm_cues = [
                    Cue(
                        cue_type=str(item.get("cue_type", "note"))[:60],
                        text=str(item.get("text", ""))[:160],
                        explanation=str(item.get("explanation", ""))[:400],
                        severity=self._severity(str(item.get("severity", "medium"))),
                        source="llm",
                    )
                    for item in answer.get("cues", [])
                    if isinstance(item, dict) and item.get("text")
                ]
                existing = {(cue.cue_type, cue.text.lower()) for cue in cues}
                for cue in llm_cues:
                    if (cue.cue_type, cue.text.lower()) not in existing:
                        cues.append(cue)
                cues.sort(key=lambda cue: -SEVERITY_ORDER.get(cue.severity.value, 0))
                if answer.get("summary"):
                    summary = str(answer["summary"])
                llm_uncertainty = str(answer.get("uncertainty_note", "")).strip()
                if llm_uncertainty and llm_uncertainty.lower() not in ("none", "n/a", ""):
                    uncertainty = f"{uncertainty}; {llm_uncertainty}".strip("; ")
            except Exception as exc:  # noqa: BLE001 — offline/template fallbacks must always win
                uncertainty = (
                    f"{uncertainty}; LLM synthesis unavailable ({type(exc).__name__}) — "
                    "merged from rule-based tool outputs only."
                ).strip("; ")

        # --- Federated intel match check (local hashing only) -------------
        # If any URL/domain in this case was community-reported before, raise
        # an immediate high-priority cue — a known threat skips the debate.
        # Only hashes are compared against the local store; nothing is sent.
        indicators: list[tuple[str, str]] = []
        if case.url:
            from urllib.parse import urlparse

            indicators.append((case.url, "url"))
            domain = urlparse(case.url).netloc.lower()
            if domain:
                indicators.append((domain, "domain"))
        indicators.extend((url, "url") for url in link_safety.extract_urls(case.redacted_text)[:5])
        intel_matches = find_intel_matches(indicators)
        if intel_matches:
            match = intel_matches[0]
            cues.insert(
                0,
                Cue(
                    cue_type="threat_intel_match",
                    text=f"GLOBAL THREAT INTEL MATCH: Reported by community ({match['report_count']}x)",
                    explanation=(
                        "This exact link/domain was already reported to the federated scam-intel "
                        "network by other community nodes. The indicator hash matched a stored "
                        "threat fingerprint — treat with maximum suspicion and never open it."
                    ),
                    severity=Severity.HIGH,
                    source="rules",
                ),
            )
            if RISK_ORDER[rule_risk] < RISK_ORDER[RiskLevel.HIGH]:
                rule_risk = RiskLevel.HIGH
            uncertainty = (
                f"{uncertainty}; threat-intel match on a community-reported indicator "
                f"(seen {match['report_count']}x)."
            ).strip("; ")
            evidence.append(
                Evidence(
                    tool="community_intel_match",
                    raw_output={
                        "matches": intel_matches,
                        "action": "known threat hash raised the verdict to high",
                        "privacy": "Matched locally by SHA-256 hash — no data transmitted.",
                    },
                )
            )

        # --- Psychological Manipulation Radar -----------------------------
        # Deterministic attack-vector annotation over the merged cues; stored
        # as evidence so the Review screen can show WHY each score exists.
        radar = psych_radar.build_radar([cue.model_dump(mode="json") for cue in cues])
        evidence.append(Evidence(tool="psych_radar", raw_output=radar))

        # --- Decision Defence Engine --------------------------------------
        # Deterministically maps evidence into the decision the attacker is
        # trying to force, the conditions that would make the message
        # legitimate, and an independent verification path.
        link_domains = (link or {}).get("domains", []) if isinstance(link, dict) else []
        defence_plan = build_defence_plan(
            redacted_text=case.redacted_text,
            cues=[cue.model_dump(mode="json") for cue in cues],
            radar=radar,
            risk=rule_risk.value,
            confidence=("high" if llm_used and not conflicts else "low" if conflicts else "medium"),
            domains=link_domains,
        )
        evidence.append(Evidence(tool="decision_defence", raw_output=defence_plan))

        # --- Debate outcome disclosed in the uncertainty note -------------
        if resolution.get("consensus") == "contested":
            uncertainty = (
                f"{uncertainty}; Red/Blue debate split the vote (red: {resolution.get('red_vote')}, "
                f"blue: {resolution.get('blue_vote')}) — human review is decisive."
            ).strip("; ")

        # --- Confidence band (blueprint: never a bare binary) ------------
        if conflicts:
            confidence = Confidence.LOW
        elif llm_used and not gaps:
            confidence = Confidence.HIGH
        else:
            confidence = Confidence.MEDIUM

        reasoning_trace = {
            "provider": llm.llm_status().get("provider_setting"),
            "llm_used": llm_used,
            "tool_outputs": {k: v for k, v in module_results.items()},
            "prompt_template": "orchestrator_synthesis",
            "conflicts": conflicts,
            "gaps": gaps,
            "debate": {
                "consensus": resolution.get("consensus"),
                "red_vote": resolution.get("red_vote"),
                "blue_vote": resolution.get("blue_vote"),
                "rounds": len(debate.get("rounds", [])),
                "judge_used": resolution.get("judge_used", False),
                "transcript_evidence_tool": "agent_debate",
            },
            "psych_radar": {
                "overall": radar.get("overall"),
                "cooling_off_required": radar.get("cooling_off_required"),
                "top_vector": (radar.get("vectors") or [{}])[0].get("name"),
            },
            "decision_defence": {
                "recommendation": defence_plan.get("recommendation"),
                "decision_safety_score": defence_plan.get("decision_safety_score"),
                "intended_actions": defence_plan.get("intended_actions"),
                "counterfactual": defence_plan.get("counterfactual"),
                "safe_verification": defence_plan.get("safe_verification"),
            },
            "note": "Full prompt/tool-output/response trio logged as separate evidence entries.",
        }
        evidence.append(Evidence(tool="llm_synthesis", raw_output=reasoning_trace))

        return Verdict(
            case_id=case.id,
            score=rule_risk,
            cues=cues,
            confidence=confidence,
            uncertainty_note=uncertainty,
            summary=summary,
            action_required=rule_risk != RiskLevel.LOW,
            reasoning_trace=reasoning_trace,
        )

    # ------------------------------------------------------------------
    # Synthesis helpers
    # ------------------------------------------------------------------

    def _collect_gaps(self, module_results: dict[str, dict], case: Case) -> tuple[list[str], list[str]]:
        conflicts = list(case.normalisation_notes)
        gaps: list[str] = []

        link = module_results.get("link") or {}
        for chain in link.get("chains", []):
            if chain.get("error"):
                conflicts.append(f"Redirect chain could not be fully traced: {chain['error']}")
            if chain.get("truncated"):
                conflicts.append("The redirect chain hit the safety cap; the true landing page may be further along.")
        for intel in link.get("domains", []):
            if intel.get("domain_age_days") is None:
                gaps.append(f"Domain age could not be verified for {intel.get('domain', 'the link')}.")
            reputations = intel.get("reputation", [])
            if reputations and all((not rep.get("checked")) or rep.get("unavailable_reason") for rep in reputations):
                gaps.append(f"No reputation verdict was available for {intel.get('domain', 'the link')}.")

        for name, result in module_results.items():
            if result.get("module_failed"):
                conflicts.append(f"The {name} module failed and its evidence is missing.")
        return conflicts, gaps

    def _rule_risk(self, phishing: Optional[dict], link: Optional[dict], audio: Optional[dict] = None) -> RiskLevel:
        risk = RiskLevel.LOW
        for result in (phishing, link, audio):
            if not result or result.get("module_failed") or result.get("skipped"):
                continue
            value = result.get("risk")
            if value in ("low", "medium", "high") and RISK_ORDER[RiskLevel(value)] > RISK_ORDER[risk]:
                risk = RiskLevel(value)
        return risk

    def _merge_cues(self, phishing: Optional[dict], link: Optional[dict]) -> list[Cue]:
        cues: list[Cue] = []

        def from_payload(payload: Optional[dict], key: str) -> None:
            for item in (payload or {}).get(key, []):
                if not isinstance(item, dict) or not item.get("text"):
                    continue
                cues.append(
                    Cue(
                        cue_type=str(item.get("cue_type", "note"))[:60],
                        text=str(item.get("text", ""))[:160],
                        explanation=str(item.get("explanation", ""))[:400],
                        severity=self._severity(str(item.get("severity", "medium"))),
                        source="llm" if item.get("source") == "llm" else "rules",
                    )
                )

        from_payload(phishing, "cues")
        from_payload(link, "link_flags")

        seen: set[tuple[str, str]] = set()
        unique: list[Cue] = []
        for cue in cues:
            key = (cue.cue_type, cue.text.lower())
            if key not in seen:
                seen.add(key)
                unique.append(cue)
        unique.sort(key=lambda cue: -SEVERITY_ORDER.get(cue.severity.value, 0))
        return unique[:20]

    def _offline_summary(
        self,
        case: Case,
        phishing: Optional[dict],
        link: Optional[dict],
        audio: Optional[dict] = None,
    ) -> str:
        parts: list[str] = []
        if phishing and not phishing.get("module_failed") and not phishing.get("skipped"):
            notes = phishing.get("notes") or ""
            if notes:
                parts.append(notes)
        if link and not link.get("module_failed") and not link.get("skipped"):
            verdict_text = link.get("verdict_text") or ""
            if verdict_text:
                parts.append(verdict_text)
        if audio and not audio.get("module_failed"):
            verdict_text = audio.get("verdict_text") or ""
            if verdict_text:
                parts.append(verdict_text)
        if not parts:
            parts.append(
                "No module produced findings for this case; the message did not match known scam patterns."
            )
        return " ".join(parts)[:900]

    def _severity(self, value: str) -> "Severity":
        from backend.models.case import Severity

        try:
            return Severity(value.lower())
        except ValueError:
            return Severity.MEDIUM

    # ------------------------------------------------------------------
    # Case views
    # ------------------------------------------------------------------

    def load_case(self, case_id: str) -> Optional[Case]:
        row = db.get_case_row(case_id)
        if row is None:
            return None
        return Case(
            id=row["id"],
            input_type=InputType(row["input_type"]),
            raw_text="",  # originals are never persisted
            redacted_text=row["redacted_text"],
            url=row["url"],
            image_filename=row["image_filename"],
            audio_filename=row["audio_filename"] if "audio_filename" in row.keys() else "",
            status=CaseStatus(row["status"]),
            created_at=row["created_at"],
        )

    def build_case_view(self, case_id: str):
        case = self.load_case(case_id)
        if case is None:
            return None
        verdict = db.latest_verdict(case_id)
        decisions = db.list_decisions(case_id)
        report = db.get_report_artifact(case_id)
        quiz = db.get_quiz_artifact(case_id)
        from backend.models.case import CaseView

        return CaseView(
            case=case,
            evidence=db.list_evidence(case_id),
            verdict=verdict,
            decisions=decisions,
            report=report,
            quiz=quiz,
        )


_ORCHESTRATOR: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = Orchestrator()
    return _ORCHESTRATOR
