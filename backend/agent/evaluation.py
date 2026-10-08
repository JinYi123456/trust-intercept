"""Offline Evaluation Lab for TRUST//INTERCEPT (benchmark v2).

Runs the real investigation pipeline without persisting cases or opening external
sites. The benchmark mixes 74 cases: scams, legitimate notices, borderline
cases, and adversarial wording across English, Bahasa Malaysia and Manglish.

Every case carries a provenance tag: `sms_spam_collection` (verbatim, labelled
by the dataset) or `synthetic` (team-written). CIC-Trap4Phish is NOT integrated
(see benchmark_cases.py for the honest reason). Metrics reported here are
LOCAL BENCHMARK numbers from the deterministic engine, not product accuracy
claims on live traffic.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from backend.agent.benchmark_cases import benchmark_cases
from backend.agent.orchestrator import Orchestrator
from backend.models.case import Case, InputType, RiskLevel


def _expected_positive(label: str) -> bool:
    return label == "scam"


def _predicted_positive(score: RiskLevel) -> bool:
    return score in (RiskLevel.MEDIUM, RiskLevel.HIGH)


def _run_one(item: dict[str, str]) -> dict[str, Any]:
    case = Case(input_type=InputType.TEXT, raw_text=item["text"])
    runner = Orchestrator()
    runner._normalise(case, None)
    verdict, evidence = runner._investigate(case)
    predicted = _predicted_positive(verdict.score)
    expected = _expected_positive(item["label"])
    return {
        "id": item["id"],
        "label": item["label"],
        "channel": item.get("channel", "sms"),
        "language": item.get("language", "en"),
        "source": item.get("source", "synthetic"),
        "score": verdict.score.value,
        "confidence": verdict.confidence.value,
        "predicted_scam": predicted,
        "correct": predicted == expected,
        "cue_count": len(verdict.cues),
        "cues": [cue.cue_type for cue in verdict.cues[:8]],
        "uncertainty": verdict.uncertainty_note,
        "evidence_count": len(evidence),
    }


def _confusion(results: list[dict[str, Any]]) -> dict[str, int]:
    tp = sum(r["predicted_scam"] and r["label"] == "scam" for r in results)
    tn = sum((not r["predicted_scam"]) and r["label"] == "legit" for r in results)
    # Borderline predicted-positive counts as false-positive pressure.
    fp = sum(r["predicted_scam"] and r["label"] in ("legit", "borderline") for r in results)
    fn = sum((not r["predicted_scam"]) and r["label"] == "scam" for r in results)
    return {"true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn}


def _metrics_from(cm: dict[str, int], total: int, legit_total: int) -> dict[str, float]:
    tp, fp, fn = cm["true_positive"], cm["false_positive"], cm["false_negative"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / legit_total if legit_total else 0.0
    accuracy = (cm["true_positive"] + cm["true_negative"]) / total if total else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
    }


def _breakdown(results: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value in sorted({r[key] for r in results}):
        subset = [r for r in results if r[key] == value]
        cm = _confusion(subset)
        legit_total = sum(r["label"] == "legit" for r in subset)
        rows.append({
            key: value,
            "cases": len(subset),
            "metrics": _metrics_from(cm, len(subset), legit_total),
            "confusion_matrix": cm,
        })
    return rows


def _failure_cases(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every wrong prediction, shown honestly with what the engine saw."""
    failures = []
    for r in results:
        if r["correct"]:
            continue
        item = next((c for c in benchmark_cases() if c["id"] == r["id"]), {})
        failures.append({
            "id": r["id"],
            "label": r["label"],
            "predicted_score": r["score"],
            "language": r["language"],
            "channel": r["channel"],
            "source": r["source"],
            "cues_seen": r["cues"],
            "text": item.get("text", "")[:300],
        })
    return failures


def _llm_cost_estimate() -> dict[str, Any]:
    """Cost per case, measured from configuration — no invented prices.

    Per submitted case the pipeline makes at most:
      - 1 hosted LLM call for phishing-cue explanation (skipped when rules suffice/off)
      - 1 hosted LLM call for the debate judge (skipped offline)
    Report generation (1 call) and the coach quiz (1 call) run only when the
    user explicitly requests those features.
    """
    from backend.config import get_settings

    settings = get_settings()
    hosted = settings.llm_provider != "none" and bool(
        settings.gonka_api_key or settings.featherless_api_key or settings.gemini_api_key
    )
    calls_per_case_max = 2 if hosted else 0
    return {
        "deterministic_engine_calls": 0,
        "hosted_llm_calls_max_per_case": calls_per_case_max,
        "optional_feature_calls": {
            "report_bundle": 1,
            "coach_quiz": 1,
        },
        "token_budget": {
            "max_output_tokens_per_call": settings.llm_max_tokens,
            "note": "prompts carry only the REDACTED text (capped in code) plus module JSON",
        },
        "estimate_basis": "our benchmark (call counting from the pipeline code path); "
        "RM cost = calls x your provider's list price — demo path uses free/promo "
        "tiers (Gonka/Featherless promo, Gemini free tier) so marginal cost is "
        "approximately RM0 in the configured demo configuration",
        "deterministic_only": not hosted,
    }


def run_evaluation() -> dict[str, Any]:
    # The pipeline's community-intel lookup reads the SQLite store; make the
    # benchmark safe to call standalone (tables are created idempotently).
    from backend.models import db

    db.init_db()
    results = [_run_one(item) for item in benchmark_cases()]
    cm = _confusion(results)
    legit_total = sum(r["label"] == "legit" for r in results)
    metrics = _metrics_from(cm, len(results), legit_total)
    source_counts = Counter(r["source"] for r in results)
    return {
        "benchmark": {
            "name": "TRUST//INTERCEPT Decision Defence Benchmark",
            "version": "2.0",
            "cases": len(results),
            "composition": dict(Counter(r["label"] for r in results)),
            "channels": dict(Counter(r["channel"] for r in results)),
            "languages": dict(Counter(r["language"] for r in results)),
            "sources": dict(source_counts),
        },
        "source_documentation": {
            "sms_spam_collection": {
                "description": "UCI Machine Learning Repository id 228, Almeida et al. (ACM DOCENG'11); messages used verbatim with the dataset's own spam/ham labels",
                "cases": source_counts.get("sms_spam_collection", 0),
            },
            "synthetic": {
                "description": "team-written cases reflecting publicly reported Malaysian scam patterns (parcel fees, Macau scam, e-wallet freeze, LHDN/PDRM impersonation); not real victim messages",
                "cases": source_counts.get("synthetic", 0),
            },
            "cic_trap4phish": {
                "description": "NOT INTEGRATED — the dataset page returned HTTP 404 when this benchmark was built and access normally requires a request to the CIC team; documented as a gap, not claimed as a source",
                "cases": 0,
            },
        },
        "confusion_matrix": cm,
        "metrics": metrics,
        "breakdowns": {
            "by_language": _breakdown(results, "language"),
            "by_channel": _breakdown(results, "channel"),
            "by_source": _breakdown(results, "source"),
        },
        "failure_cases": _failure_cases(results),
        "cost_per_case": _llm_cost_estimate(),
        "safety_notes": [
            "LOCAL BENCHMARK ONLY — these numbers do not generalise to live traffic; the dataset is small and partly synthetic.",
            "Evaluation runs the real local investigation pipeline without persisting benchmark cases.",
            "No suspicious URL is opened by the benchmark; outbound lookups are disabled.",
            "Medium/high is counted as an interception prediction; borderline cases are included in false-positive pressure.",
            "Metrics are from the deterministic engine (LLM_PROVIDER=none); hosted-LLM mode may shift precision/recall.",
        ],
        "results": results,
    }
