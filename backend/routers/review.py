"""Review — the human-in-the-loop gate (Framework section 05).

STRUCTURAL GUARANTEE
--------------------
Every module returns a Verdict carrying `action_required` but NEVER
`action_taken` — that field does not exist on the Verdict model. The only code
path that records an action taken is a Decision, and Decisions are created by
exactly one function (Orchestrator.build_decision), reachable exclusively
through POST /case/{id}/decision below. There is no code path from "module
finishes" to "report sent" or "contact blocked".

- Verdict -> Decision is a one-way gate: the orchestrator can only propose.
- Every Decision stores the verdict snapshot the user actually saw, so the
  audit trail survives later edits.
- A `disagree` decision re-runs the pipeline with the correction noted and
  APPENDS a new verdict — the original is preserved (verdicts are
  append-only), satisfying the "disagreement is evidence" rule.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.agent.modules import awareness_coach, scam_reporter
from backend.agent.modules.link_safety import extract_urls
from backend.agent.orchestrator import get_orchestrator
from backend.models import db
from backend.models.case import (
    CaseView,
    DecisionRequest,
    Evidence,
    HumanAction,
    Quiz,
    QuizSubmitRequest,
    QuizAttempt,
)
from backend.routers.metrics import record_threat_indicator
from backend.tools import sandbox_recon
from backend.agent.security import tool_url_policy

router = APIRouter(tags=["review"])


@router.post(
    "/case/{case_id}/decision",
    response_model=CaseView,
    summary="Record the human decision — the ONLY endpoint that writes action_taken",
)
def record_decision(case_id: str, request: DecisionRequest) -> CaseView:
    orchestrator = get_orchestrator()

    if orchestrator.load_case(case_id) is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    if db.latest_verdict(case_id) is None:
        raise HTTPException(status_code=409, detail=f"Case {case_id} has no verdict to review yet.")
    if request.human_action == HumanAction.DISAGREE_RECHECK and not request.correction.strip():
        raise HTTPException(
            status_code=422,
            detail="The disagree_recheck action requires a non-empty `correction` describing what was wrong.",
        )

    # Snapshot + action_taken text are created HERE and nowhere else.
    decision = orchestrator.build_decision(
        case_id=case_id,
        human_action=request.human_action,
        correction=request.correction.strip(),
        decided_by=request.decided_by,
    )

    case = orchestrator.load_case(case_id)
    verdict = db.latest_verdict(case_id)

    if request.human_action == HumanAction.REPORT and case is not None:
        # Defensive action 1: the redacted report bundle (Module 3).
        bundle = scam_reporter.run(case, verdict)
        db.save_artifact(case_id, "report", bundle.model_dump(mode="json"))
        db.add_evidence(
            case_id,
            Evidence(
                tool="module_3_reporter",
                raw_output={
                    "action": "report_bundle_generated",
                    "evidence_hash": bundle.evidence_hash,
                    "cues_included": len(bundle.cues_detected),
                    "note": "TRUST//INTERCEPT prepares it; the human sends it. Nothing is transmitted automatically.",
                },
            ),
        )

        # Federated Scam Intelligence Network: contribute the anonymous
        # SHA-256 of the malicious URL/domain to the local intel store.
        # No message content and no personal data ever leave the device —
        # only the un-linkable indicator hash is recorded.
        intel_contributed: list[str] = []
        from backend.agent.modules.link_safety import extract_urls

        for url in extract_urls(case.redacted_text)[:5]:
            result = record_threat_indicator(url, kind="url", risk=verdict.score.value)
            intel_contributed.append(result["hash"][:12])
        if case.url:
            from urllib.parse import urlparse

            domain = urlparse(case.url).netloc.lower()
            if domain:
                record_threat_indicator(domain, kind="domain", risk=verdict.score.value)
                intel_contributed.append(domain)
        db.add_evidence(
            case_id,
            Evidence(
                tool="community_intel",
                raw_output={
                    "action": "threat_indicator_hashes_shared",
                    "indicators": intel_contributed,
                    "privacy": "SHA-256 hashes only — no message content, no personal data.",
                },
            ),
        )

    elif request.human_action == HumanAction.DISAGREE_RECHECK:
        # Defensive action 2: re-run with the correction noted (original preserved).
        orchestrator.rerun_with_correction(case_id, request.correction.strip())

    # LOOKS_SAFE / BLOCK_WARN need no side effects: the warning is the
    # plain-language guidance already on the verdict (guidance only, never
    # device-level enforcement).

    db.add_decision(decision)
    view = orchestrator.build_case_view(case_id)
    if view is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Case vanished during decision handling.")
    return view


@router.post(
    "/case/{case_id}/recon",
    summary="Human-requested Honeypot Sandbox Recon on a high-risk URL (counter-intel for police reporting)",
)
def run_sandbox_recon(case_id: str) -> dict:
    """Isolated one-shot probe of the scammer's infrastructure.

    Gated: only reachable by an explicit user action (the Review-screen
    button), only when the latest verdict rates the case HIGH, and the probe
    itself refuses without outbound access. The result is stored as
    `sandbox_recon` evidence — infrastructure facts only, no user data.
    """
    orchestrator = get_orchestrator()
    case = orchestrator.load_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    verdict = db.latest_verdict(case_id)
    if verdict is None:
        raise HTTPException(status_code=409, detail="Case has no verdict to inspect.")
    if verdict.score.value != "high":
        raise HTTPException(
            status_code=422,
            detail="Sandbox recon is reserved for HIGH-risk cases — this case does not qualify.",
        )

    candidates = ([case.url] if case.url else []) + extract_urls(case.redacted_text)
    target = next((url for url in candidates if url.startswith("http")), None)
    if not target:
        raise HTTPException(status_code=422, detail="No URL present in this case to probe.")
    policy = tool_url_policy(target)
    if not policy["allowed"]:
        raise HTTPException(status_code=422, detail="Sandbox recon blocked by outbound target safety policy: " + "; ".join(policy["reasons"]))

    result = sandbox_recon.probe(target, verdict.score.value)
    db.add_evidence(case_id, Evidence(tool="sandbox_recon", raw_output=result))
    return result


@router.post(
    "/case/{case_id}/coach",
    response_model=Quiz,
    summary="Launch the Module 4 awareness quiz for the detected pattern",
)
def launch_coach(case_id: str) -> Quiz:
    orchestrator = get_orchestrator()
    case = orchestrator.load_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    verdict = db.latest_verdict(case_id)
    if verdict is None:
        raise HTTPException(status_code=409, detail=f"Case {case_id} has no verdict — investigate it first.")

    quiz = awareness_coach.run(case, verdict)
    db.save_artifact(case_id, "quiz", quiz.model_dump(mode="json"))
    db.add_evidence(
        case_id,
        Evidence(
            tool="module_4_coach",
            raw_output={
                "pattern_name": quiz.pattern_name,
                "generated_by_llm": quiz.generated_by_llm,
                "question_count": len(quiz.questions),
            },
        ),
    )
    return quiz


@router.post(
    "/case/{case_id}/coach/submit",
    tags=["awareness"],
    summary="Score a completed awareness quiz and update pattern mastery",
)
def submit_coach(case_id: str, request: QuizSubmitRequest) -> dict:
    orchestrator = get_orchestrator()
    case = orchestrator.load_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    quiz = db.get_quiz_artifact(case_id)
    if quiz is None or not quiz.questions:
        raise HTTPException(status_code=409, detail="No awareness quiz is available for this case.")
    if len(request.answers) != len(quiz.questions):
        raise HTTPException(status_code=422, detail="Submit exactly one answer per quiz question.")

    correct = 0
    missed: list[int] = []
    focus_areas: list[str] = []
    for index, selected in enumerate(request.answers):
        question = quiz.questions[index]
        if selected == question.correct_index:
            correct += 1
        else:
            missed.append(index)
            focus_areas.append(awareness_coach.focus_for_question(quiz.pattern_name, question))

    total = len(quiz.questions)
    accuracy = round(correct / total, 3) if total else 0.0
    # Keep only distinct focus areas so the learning record stays compact.
    focus_areas = list(dict.fromkeys(focus_areas))
    attempt = QuizAttempt(
        case_id=case_id, pattern_name=quiz.pattern_name, score=correct, total=total,
        accuracy=accuracy, missed_indexes=missed, focus_areas=focus_areas,
    )
    db.save_quiz_attempt(attempt)
    mastery = db.get_pattern_mastery(quiz.pattern_name)
    return {
        "attempt": attempt.model_dump(mode="json"),
        "mastery": mastery.model_dump(mode="json"),
        "message": (
            "Pattern mastered — keep using independent verification." if mastery.mastery_band == "mastered"
            else "Recognition is building. Your next training should target the missed cues."
        ),
        "privacy": "Only quiz outcomes and pattern-level focus areas are stored; answer text and case PII are not persisted.",
    }


@router.get(
    "/case/{case_id}/coach/mastery",
    tags=["awareness"],
    summary="Read the current mastery state for this case's scam pattern",
)
def coach_mastery(case_id: str) -> dict:
    orchestrator = get_orchestrator()
    if orchestrator.load_case(case_id) is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    quiz = db.get_quiz_artifact(case_id)
    if quiz is None:
        raise HTTPException(status_code=409, detail="No awareness quiz is available for this case.")
    return db.get_pattern_mastery(quiz.pattern_name).model_dump(mode="json")
