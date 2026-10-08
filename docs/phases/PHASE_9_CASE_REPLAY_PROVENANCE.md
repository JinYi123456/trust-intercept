# Phase 9 — Case Replay & Provenance

## Goal
Turn every investigation into an auditable, deterministic replay record.

## What changed
- Added `backend/agent/provenance.py` to reconstruct a case timeline from persisted, redacted state.
- Added provenance metadata to `CaseView`.
- Added `GET /case/{case_id}/replay` for an explicit replay/audit payload.
- Added the `CaseReplay` UI to Review.
- Every evidence step gets an evidence fingerprint and actor/stage attribution.
- A manifest SHA-256 makes the persisted replay snapshot tamper-evident for later comparison.

## Safety boundary
Replay is **not** a re-execution engine. It never:
- opens suspicious URLs;
- reruns network tools;
- calls an LLM;
- contacts a sender;
- reveals original PII.

It reconstructs what the system already recorded after redaction.

## Why this matters
The reviewer can now answer:
1. What happened first?
2. Which tool or agent produced each evidence item?
3. Which verdict versions existed?
4. When did the human approve an action?
5. Can the case be replayed later without triggering new side effects?

This makes the agentic workflow auditable rather than merely explainable.
