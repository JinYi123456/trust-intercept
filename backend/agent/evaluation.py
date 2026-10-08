"""Offline Evaluation Lab for TRUST//INTERCEPT.

Runs the real investigation pipeline without persisting cases or opening external
sites. The benchmark deliberately mixes scams, legitimate notices, borderline
cases, and adversarial wording to measure false-positive control.
"""
from __future__ import annotations

from typing import Any

from backend.agent.orchestrator import Orchestrator
from backend.models.case import Case, InputType, RiskLevel

BENCHMARK = [
    {"id": "scam_parcel", "label": "scam", "text": "SINGPOST: parcel HELD. Pay $1.99 within 24 hours or it will be returned. https://bit.ly/pay-now Enter your IC number and OTP."},
    {"id": "scam_bank", "label": "scam", "text": "MAYBANK SECURITY: Your account will be suspended today. Verify immediately at https://bit.ly/security-check and provide your password and OTP."},
    {"id": "legit_courier", "label": "legit", "text": "DHL Express: Your shipment D-9823 is out for delivery today between 2-4 PM. Track it at https://www.dhl.com/track/D-9823. No action needed."},
    {"id": "legit_bank", "label": "legit", "text": "Maybank: Your monthly e-statement is now available in the MAE app. Open the app directly to view it. We will never ask for your password or OTP by SMS."},
    {"id": "borderline_delivery", "label": "borderline", "text": "Your parcel is ready for delivery. Please check the delivery address in the official courier app if you are expecting a shipment. No payment is requested."},
    {"id": "adversarial_safe", "label": "legit", "text": "Security reminder: criminals may use URGENT language, OTP requests and payment links. This notice asks you to do nothing and verify through the official app."},
]


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
        "score": verdict.score.value,
        "confidence": verdict.confidence.value,
        "predicted_scam": predicted,
        "correct": predicted == expected,
        "cue_count": len(verdict.cues),
        "cues": [cue.cue_type for cue in verdict.cues[:8]],
        "uncertainty": verdict.uncertainty_note,
        "evidence_count": len(evidence),
    }


def run_evaluation() -> dict[str, Any]:
    results = [_run_one(item) for item in BENCHMARK]
    tp = sum(r["predicted_scam"] and r["label"] == "scam" for r in results)
    tn = sum((not r["predicted_scam"]) and r["label"] == "legit" for r in results)
    fp = sum(r["predicted_scam"] and r["label"] in ("legit", "borderline") for r in results)
    fn = sum((not r["predicted_scam"]) and r["label"] == "scam" for r in results)
    positive_actual = tp + fn
    predicted_positive = tp + fp
    precision = tp / predicted_positive if predicted_positive else 0.0
    recall = tp / positive_actual if positive_actual else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    legit_total = sum(r["label"] == "legit" for r in results)
    fpr = fp / legit_total if legit_total else 0.0
    accuracy = sum(r["correct"] for r in results) / len(results)
    return {
        "benchmark": {"name": "TRUST//INTERCEPT Decision Defence Benchmark", "version": "1.0", "cases": len(results)},
        "confusion_matrix": {"true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn},
        "metrics": {"accuracy": round(accuracy, 4), "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "false_positive_rate": round(fpr, 4)},
        "safety_notes": [
            "Evaluation runs the real local investigation pipeline without persisting benchmark cases.",
            "No suspicious URL is opened by the benchmark.",
            "Medium/high is counted as an interception prediction; borderline cases are included in false-positive pressure.",
        ],
        "results": results,
    }
