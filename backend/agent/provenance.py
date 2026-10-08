"""Auditable provenance and replay representation for TRUST//INTERCEPT cases.

The replay is intentionally a reconstruction of persisted, redacted state. It
never re-executes tools, follows URLs, calls an LLM, or exposes original PII.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.models import db


def _canonical(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def build_case_provenance(case_id: str) -> dict[str, Any]:
    case = db.get_case_row(case_id)
    if case is None:
        raise KeyError(f"Case {case_id} not found.")

    evidence = db.list_evidence(case_id)
    verdicts = db.list_verdicts(case_id)
    decisions = db.list_decisions(case_id)

    steps: list[dict[str, Any]] = [
        {
            "sequence": 1,
            "stage": "INTAKE",
            "actor": "trust_gateway",
            "event": "case_created",
            "status": "completed",
            "details": {"input_type": case["input_type"]},
        }
    ]

    for index, entry in enumerate(evidence, start=2):
        output = entry.raw_output or {}
        steps.append(
            {
                "sequence": index,
                "stage": _stage_for_tool(entry.tool),
                "actor": _actor_for_tool(entry.tool),
                "event": entry.tool,
                "status": "completed",
                "collected_at": entry.collected_at.isoformat(),
                "evidence_fingerprint": hashlib.sha256(_canonical(output).encode()).hexdigest(),
                "details": _safe_summary(output),
            }
        )

    base = len(steps) + 1
    for offset, verdict in enumerate(verdicts):
        steps.append(
            {
                "sequence": base + offset,
                "stage": "DECISION SYNTHESIS",
                "actor": "evidence_arbiter",
                "event": "verdict_created",
                "status": "completed",
                "created_at": verdict.created_at.isoformat(),
                "details": {
                    "risk": verdict.score.value,
                    "confidence": verdict.confidence.value,
                    "cue_count": len(verdict.cues),
                    "action_required": verdict.action_required,
                },
            }
        )

    base = len(steps) + 1
    for offset, decision in enumerate(decisions):
        steps.append(
            {
                "sequence": base + offset,
                "stage": "HUMAN APPROVAL",
                "actor": "human",
                "event": "decision_recorded",
                "status": "completed",
                "created_at": decision.decided_at.isoformat(),
                "details": {
                    "human_action": decision.human_action.value,
                    "decided_by": decision.decided_by,
                    "correction_present": bool(decision.correction),
                },
            }
        )

    manifest = {
        "case_id": case_id,
        "schema_version": "provenance.v1",
        "redacted_case": {
            "input_type": case["input_type"],
            "redacted_text": case["redacted_text"],
            "url_present": bool(case["url"]),
            "created_at": case["created_at"],
        },
        "steps": steps,
    }
    digest = hashlib.sha256(_canonical(manifest).encode()).hexdigest()

    return {
        "schema_version": "provenance.v1",
        "case_id": case_id,
        "replayable": True,
        "replay_mode": "persisted_redacted_state",
        "step_count": len(steps),
        "evidence_count": len(evidence),
        "verdict_count": len(verdicts),
        "decision_count": len(decisions),
        "integrity_hash": digest,
        "steps": steps,
        "safety_boundary": "Replay reads persisted redacted evidence only. It does not open URLs, rerun tools, call external services, or reveal original PII.",
    }


def _stage_for_tool(tool: str) -> str:
    if tool in {"qr_decode", "ocr", "pii_redact"}:
        return "NORMALISATION"
    if tool in {"route", "router"}:
        return "ROUTING"
    if tool in {"debate", "agent_debate", "counterfactual_verification", "decision_defence", "psych_radar"}:
        return "AGENT INVESTIGATION"
    if tool in {"llm_synthesis"}:
        return "DECISION SYNTHESIS"
    return "TOOL INVESTIGATION"


def _actor_for_tool(tool: str) -> str:
    if tool in {"qr_decode", "ocr", "pii_redact"}:
        return "local_normalizer"
    if tool == "llm_synthesis":
        return "evidence_arbiter"
    if tool in {"debate", "agent_debate"}:
        return "hunter_skeptic_verifier"
    if tool == "counterfactual_verification":
        return "verification_agent"
    if tool == "decision_defence":
        return "decision_defence_agent"
    return tool


def _safe_summary(output: dict[str, Any]) -> dict[str, Any]:
    """Keep replay useful without duplicating full potentially sensitive output."""
    allowed = {
        "engine", "urls", "payloads_found", "mean_confidence", "items_redacted",
        "placeholders", "risk", "checked", "malicious", "detail", "domains",
        "recommendation", "decision_safety_score", "status", "verification_state",
        "risk_delta", "claim", "independent_source", "expected_evidence",
        "actual_evidence", "confidence", "techniques", "conflict_count",
    }
    result = {key: output[key] for key in allowed if key in output}
    return result
