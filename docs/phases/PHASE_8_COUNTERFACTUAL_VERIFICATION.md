# Phase 8 — Counterfactual Verification Engine

## Goal
Turn the question **“If this were legitimate, what independent evidence should exist?”** into a structured, auditable verification task.

## Changes
- `backend/agent/counterfactual.py` — deterministic verification engine.
- `frontend/src/components/CounterfactualVerification.jsx` — verification observatory UI.
- `backend/agent/orchestrator.py` — records verification evidence and trace metadata.
- `frontend/src/pages/Review.jsx` — displays the new engine inside Decision Defence.

## States
- `NOT_CHECKED` — requires a human using an independent channel.
- `SUPPORTS` — an available automated check supports the claim, but does not prove identity.
- `CONTRADICTS` — available evidence conflicts with the claim.
- `INCONCLUSIVE` — evidence exists but cannot establish legitimacy.

## Safety boundary
The engine never opens a suspicious URL, contacts a sender, replies to a message, or fabricates external confirmation. It tells the user to verify through a trusted channel that was not supplied by the suspicious message.

## Risk policy
Contradictory automated evidence may raise risk. Supportive evidence cannot silently make a suspicious case safe; any risk-lowering interpretation remains subject to human review.

## Evidence model
Each verification item records the claim, independent source, expected evidence, evidence actually found, state, and risk impact.
