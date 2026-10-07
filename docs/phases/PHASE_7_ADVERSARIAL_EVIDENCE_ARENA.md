# Phase 7 — Adversarial Evidence Arena

## Goal

Make the Hunter / Skeptic / Verifier protocol auditable rather than theatrical.

## Changes

- Added a challenge matrix to the stored `agent_debate` resolution.
- Records Hunter evidence count, Skeptic evidence count, conflict count, shared techniques, verifier tests, and the explicit overturn condition.
- Added `EvidenceChallengeMatrix.jsx` to the Review screen.
- The UI lets a reviewer switch between the attack case and benign/false-positive case while keeping the verifier's decision-changing tests visible.
- Existing deterministic/offline debate remains the source of truth; no new LLM dependency is required.

## Safety rule

The debate does not silently lower the rule-based risk floor. A disagreement is disclosed as contested evidence, and the verifier identifies what independent evidence could change the conclusion.
