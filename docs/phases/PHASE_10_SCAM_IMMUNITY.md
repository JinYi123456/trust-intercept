# Phase 10 — Scam Immunity / Adaptive Awareness

## Purpose

TRUST//INTERCEPT now turns a completed investigation into a short, pattern-specific learning loop.
The goal is not to award a generic quiz score. The system records whether the user can recognize the
same manipulation pattern and identifies the next training focus.

## Flow

`REAL CASE → DETECTED PATTERN → MICRO-QUIZ → USER PREDICTION → SCORE → MISSED CUES → PATTERN MASTERY → NEXT FOCUS`

## Privacy boundary

Only aggregate learning outcomes are persisted:

- pattern name
- score / total
- accuracy
- missed question indexes
- pattern-level focus areas
- completion timestamp

No quiz answer text, original case text, PII, sender identity, or user account identifier is stored by
this feature.

## Mastery bands

- `developing`: below 60% aggregate accuracy
- `building`: 60–79%
- `strong`: 80–89%
- `mastered`: 90%+ with at least two attempts

The thresholds are product heuristics, not a clinical or educational certification.

## Safety

The coach never asks the user to interact with a suspicious URL or contact a suspected scammer.
It reinforces independent verification, urgency resistance, credential/OTP protection, and evidence-based
recognition.

## APIs

- `POST /case/{case_id}/coach` — generate the pattern-specific quiz
- `POST /case/{case_id}/coach/submit` — server-score the completed attempt and update mastery
- `GET /case/{case_id}/coach/mastery` — retrieve the current pattern mastery
