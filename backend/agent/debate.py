"""Evidence Arena — adversarial scam analysis with Red, Blue and Verifier roles.

Before the final verdict is synthesised, adversarial roles examine the
same evidence and argue opposite cases:

* **RedAgent** — the prosecution. Tries to prove the artefact IS a
  sophisticated scam (or a false-flag designed to look like one), citing the
  manipulation techniques a fraudster would have built in.
* **BlueAgent** — the defence. Hunts for false positives: genuine courier
  formats, official domains, normal business wording, organic human phrasing.

The Orchestrator collects both agents' outputs (plus, when an LLM is
configured, a judge consolidation), resolves conflicts, and stores the ENTIRE
debate transcript in the case evidence (`tool="agent_debate"`) so the Review
screen can display exactly why the verdict landed where it did.

Deterministic guarantee: with LLM_PROVIDER=none the debate still runs — each
side argues from the REAL tool outputs using deterministic heuristics (rule
evidence vs. exculpatory signals), so the demo never fails offline. The
transcript records which engine produced each argument.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.agent import llm
from backend.models.case import Evidence

DEBATE_TOOL = "agent_debate"

# Cue types that only make sense as prosecution evidence.
_ATTACK_CUES = {
    "urgency_pressure", "credential_request", "payment_request", "disguised_link",
    "url_shortener", "too_good_to_be_true", "prize_bait", "threat_language",
    "authority_spoof", "otp_request", "brand_impersonation",
}


def _argument_from_cue(cue: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim": f"Message carries a classic manipulation cue: {cue.get('cue_type', 'unknown')}.",
        "evidence_quote": str(cue.get("text", ""))[:160],
        "technique": str(cue.get("cue_type", "unknown"))[:60],
        "strength": str(cue.get("severity", "medium")) if cue.get("severity") in ("low", "medium", "high") else "moderate",
        "engine": "deterministic",
    }


def _deterministic_red(modules: dict[str, Any], redacted_text: str) -> dict[str, Any]:
    """Prosecution case built purely from logged module evidence."""
    arguments: list[dict[str, Any]] = []
    phishing = modules.get("phishing") or {}
    for cue in (phishing.get("cues") or [])[:6]:
        if isinstance(cue, dict) and cue.get("text"):
            arguments.append(_argument_from_cue(cue))
    link = modules.get("link") or {}
    for flag in (link.get("link_flags") or [])[:4]:
        if isinstance(flag, dict) and flag.get("text"):
            arguments.append(_argument_from_cue(flag))
    for chain in link.get("chains") or []:
        if isinstance(chain, dict) and chain.get("truncated"):
            arguments.append({
                "claim": "The redirect chain hit the safety cap — the true landing page is hidden further along.",
                "evidence_quote": chain.get("start_url", "")[:160],
                "technique": "disguised_destination",
                "strength": "moderate",
                "engine": "deterministic",
            })
    if not arguments:
        arguments.append({
            "claim": "No direct manipulation cues found — but absence of cues is not proof of safety.",
            "evidence_quote": (redacted_text or "")[:120],
            "technique": "residual_risk",
            "strength": "weak",
            "engine": "deterministic",
        })
    # Vote reflects actual attack-evidence strength: high only when a strong
    # (high-severity) manipulation cue exists, medium for moderate cues, low
    # when only the residual-risk argument is available. This keeps the debate
    # from inflating clean cases.
    strengths = [a["strength"] for a in arguments]
    if "high" in strengths:
        red_vote = "high"
    elif any(s in ("moderate", "medium") for s in strengths) and not (
        len(arguments) == 1 and arguments[0]["technique"] == "residual_risk"
    ):
        red_vote = "medium"
    else:
        red_vote = "low"
    return {
        "position": "scam",
        "score_vote": red_vote,
        "arguments": arguments[:6],
        "rebuttals": [],
        "notes": "Deterministic prosecution case assembled from logged module evidence (offline mode).",
    }


def _deterministic_blue(modules: dict[str, Any], redacted_text: str) -> dict[str, Any]:
    """Defence case built purely from logged module evidence."""
    arguments: list[dict[str, Any]] = []
    link = modules.get("link") or {}
    for intel in link.get("domains") or []:
        if not isinstance(intel, dict):
            continue
        age = intel.get("domain_age_days")
        if age is not None and age > 365:
            arguments.append({
                "claim": f"Domain {intel.get('domain', '')} is over a year old — long-lived infrastructure, not a burn domain.",
                "evidence_quote": f"domain_age_days={age}",
                "technique": "domain_age_ok",
                "strength": "moderate",
                "engine": "deterministic",
            })
        for rep in intel.get("reputation") or []:
            if isinstance(rep, dict) and rep.get("checked") and not rep.get("malicious"):
                arguments.append({
                    "claim": f"Reputation engines reported no malicious verdict for {intel.get('domain', '')}.",
                    "evidence_quote": str(rep.get("detail", "checked, not malicious"))[:160],
                    "technique": "reputation_clean",
                    "strength": "moderate",
                    "engine": "deterministic",
                })
    for chain in link.get("chains") or []:
        if isinstance(chain, dict) and not chain.get("truncated") and len(chain.get("hops") or []) <= 1:
            arguments.append({
                "claim": "The link resolves directly with no redirect chain — nothing is being hidden.",
                "evidence_quote": chain.get("start_url", "")[:160],
                "technique": "no_redirects",
                "strength": "moderate",
                "engine": "deterministic",
            })
    phishing = modules.get("phishing") or {}
    if not (phishing.get("cues") or []):
        arguments.append({
            "claim": "The phishing rule library matched zero manipulation cues in the message.",
            "evidence_quote": "no cues matched",
            "technique": "no_manipulation_cues",
            "strength": "strong",
            "engine": "deterministic",
        })
    if not arguments:
        arguments.append({
            "claim": "Some risk signals exist, but no legitimate-sender check has exonerated the message yet.",
            "evidence_quote": (redacted_text or "")[:120],
            "technique": "unresolved",
            "strength": "weak",
            "engine": "deterministic",
        })
    return {
        "position": "legitimate",
        "score_vote": "low" if any(a["strength"] == "strong" for a in arguments) else "medium",
        "arguments": arguments[:6],
        "rebuttals": [],
        "notes": "Deterministic defence case assembled from logged module evidence (offline mode).",
    }


def _condense_argument(argument: dict[str, Any]) -> str:
    """One-line summary of an agent argument for the opponent's prompt context."""
    return (
        f"[{argument.get('technique', '?')}|{argument.get('strength', '?')}] "
        f"{argument.get('claim', '')} (evidence: {argument.get('evidence_quote', '')})"
    )


def _llm_round(
    side: str,
    redacted_text: str,
    modules: dict[str, Any],
    opponent_argument: str,
    round_number: int,
    max_rounds: int,
) -> Optional[dict[str, Any]]:
    """One LLM debate round for ``side`` (red|blue). None when unavailable."""
    prompt_name = "debate_red" if side == "red" else "debate_blue"
    try:
        answer = llm.generate(
            prompt_name,
            {
                "redacted_text": redacted_text[:3000],
                "modules_json": json.dumps(modules, ensure_ascii=False, indent=2)[:3500],
                "opponent_argument": (opponent_argument or "")[:1200],
                "round_number": round_number,
                "max_rounds": max_rounds,
            },
        )
    except Exception:  # noqa: BLE001 — deterministic fallback below
        return None
    answer.setdefault("position", "scam" if side == "red" else "legitimate")
    answer.setdefault("arguments", [])
    answer.setdefault("rebuttals", [])
    answer.setdefault("notes", "")
    answer["engine"] = answer.get("provider", "llm")
    for item in answer.get("arguments", []) or []:
        if isinstance(item, dict):
            item.setdefault("engine", "llm")
    return answer


def _llm_judge(redacted_text: str, transcript: dict[str, Any], modules: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        answer = llm.generate(
            "debate_judge",
            {
                "redacted_text": redacted_text[:2500],
                "debate_json": json.dumps(transcript, ensure_ascii=False, indent=2)[:4000],
                "modules_json": json.dumps(modules, ensure_ascii=False, indent=2)[:2500],
            },
        )
    except Exception:  # noqa: BLE001
        return None
    answer.setdefault("consensus", "contested")
    answer.setdefault("winning_arguments", [])
    return answer


def _vote_tuple(side: str, payload: dict[str, Any]) -> tuple[int, str]:
    """Map an agent's score_vote to (severity, label); scams win ties."""
    vote = str(payload.get("score_vote", "medium")).lower()
    if vote not in ("low", "medium", "high"):
        vote = "medium"
    severity = {"low": 0, "medium": 1, "high": 2}[vote]
    return (severity, vote)


def _deterministic_verifier(modules: dict[str, Any], redacted_text: str) -> dict[str, Any]:
    """Third role: identify evidence that could overturn the current view."""
    link = modules.get("link") or {}
    phishing = modules.get("phishing") or {}
    tests = [
        "Verify the claimed sender through an independently sourced official channel.",
        "Check whether the official account/order system shows the same event.",
        "If a URL is involved, inspect the final destination and organisation identity before visiting it.",
    ]
    if phishing.get("cues"):
        tests.append("A benign explanation must account for the exact quoted manipulation cues, not merely look plausible.")
    if link.get("domains"):
        tests.append("A clean reputation result cannot prove legitimacy; identity and request context must also match.")
    return {
        "position": "verification",
        "tests": tests[:5],
        "overturn_condition": "Independent evidence from a trusted channel contradicts the suspicious request.",
        "engine": "deterministic",
    }


def run_debate(redacted_text: str, modules: dict[str, Any], evidence: list[Evidence]) -> dict[str, Any]:
    """Full Red vs Blue debate. Returns the debate transcript dict (also logged
    as an evidence entry with tool=agent_debate).

    Resolution policy (documented for the audit trail):
    - Final score starts from the rule-based module risk (the tools' floor).
    - Each agent votes; the higher vote may RAISE the score, never lower the
      rule-based floor — defence agents protect against false positives, they
      cannot silence real tool evidence.
    - A judge consolidation (LLM mode) refines confidence and summary.
    """
    max_rounds = 2
    transcript: dict[str, Any] = {"rounds": [], "agents": {}}
    red_arguments: list[str] = []   # condensed, for the opponent's next-round rebuttals
    blue_arguments: list[str] = []

    # --- Round 1 & 2: agents argue, rebutting each other --------------------
    for round_number in range(1, max_rounds + 1):
        # Free-first policy: the adversarial roles are deterministic and use
        # the real tool outputs directly. This avoids burning multiple hosted
        # LLM calls just to create theatrical debate. A single optional judge
        # call below can arbitrate the completed evidence arena.
        red = _deterministic_red(modules, redacted_text)
        blue = _deterministic_blue(modules, redacted_text)

        verifier = _deterministic_verifier(modules, redacted_text)
        transcript["rounds"].append({
            "round": round_number,
            "red": red,
            "blue": blue,
            "verifier": verifier,
        })
        transcript["agents"] = {
            "red": {"position": red.get("position", "scam"), "score_vote": red.get("score_vote", "medium")},
            "blue": {"position": blue.get("position", "legitimate"), "score_vote": blue.get("score_vote", "medium")},
            "verifier": {"position": "verification", "engine": "deterministic"},
        }
        red_arguments = [_condense_argument(a) for a in (red.get("arguments") or [])]
        blue_arguments = [_condense_argument(a) for a in (blue.get("arguments") or [])]

    # --- Deterministic consolidation (always runs) ---------------------------
    red_final = transcript["rounds"][-1]["red"]
    blue_final = transcript["rounds"][-1]["blue"]
    red_vote_severity, red_vote_label = _vote_tuple("red", red_final)
    blue_vote_severity, blue_vote_label = _vote_tuple("blue", blue_final)

    # Raise policy: only the RED (prosecution) vote can raise the final risk —
    # that is the prosecution's role. BLUE exists to protect against false
    # positives and can never inflate the score. The orchestrator combines
    # this with the rule-based module floor (which the debate never lowers).
    debate_floor = red_vote_severity
    consensus = (
        "unanimous_scam" if red_vote_severity >= 2 and blue_vote_severity >= 2
        else "unanimous_safe" if red_vote_severity == 0 and blue_vote_severity == 0
        else "contested"
    )

    # At most ONE optional hosted call per evidence arena.
    judge: Optional[dict[str, Any]] = _llm_judge(redacted_text, transcript, modules)

    red_args = red_final.get("arguments") or []
    blue_args = blue_final.get("arguments") or []
    verifier_final = transcript["rounds"][-1].get("verifier") or {}

    # Phase 7: turn the debate into an auditable challenge matrix. Each side
    # exposes what it is actually relying on, while the verifier states what
    # independent evidence could overturn the current position. This is data
    # for the UI, not a second verdict engine.
    red_techniques = {str(a.get("technique", "")) for a in red_args if isinstance(a, dict)}
    blue_techniques = {str(a.get("technique", "")) for a in blue_args if isinstance(a, dict)}
    shared_techniques = sorted(red_techniques & blue_techniques - {""})
    conflict_count = len(red_args) + len(blue_args)
    if red_vote_label != blue_vote_label:
        conflict_count += 1

    transcript["resolution"] = {
        "red_vote": red_vote_label,
        "blue_vote": blue_vote_label,
        "debate_floor_severity": debate_floor,
        "consensus": consensus,
        "judge_used": judge is not None,
        "challenge_matrix": {
            "red_evidence_count": len(red_args),
            "blue_evidence_count": len(blue_args),
            "shared_techniques": shared_techniques,
            "conflict_count": conflict_count,
            "verifier_tests": verifier_final.get("tests", []),
            "overturn_condition": verifier_final.get("overturn_condition", "Independent trusted evidence contradicts the suspicious request."),
        },
        "policy": (
            "The debate may RAISE the final risk above the rule-based module floor; it may "
            "never lower it. Unresolved contests keep the higher vote and are disclosed in "
            "the verdict's uncertainty note."
        ),
    }
    if judge is not None:
        transcript["resolution"]["judge"] = judge

    evidence.append(Evidence(tool=DEBATE_TOOL, raw_output=transcript))
    return transcript
