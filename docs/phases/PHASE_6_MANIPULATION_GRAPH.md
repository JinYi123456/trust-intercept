# Phase 6 — Manipulation Graph™

## Goal
Turn the existing deterministic attack-chain data into an interactive, evidence-linked decision aid. This phase reuses the `attack_chain.nodes`, `attack_chain.edges`, `verdict.cues`, intended actions, and recommendation already produced by the backend.

## User-facing behaviour
- Select a stage in the attack chain to inspect its meaning.
- Display matching recorded cue evidence when a cue type maps to that stage.
- Show the preceding/following recorded edge context.
- Suggest a safe action that can interrupt the chain at the selected stage.
- Explicitly label unmatched cues as not directly linked and inferred intent as a rule-based hypothesis, not proof.
- Keep the graph usable on narrow screens with horizontal scrolling.

## Safety constraints
- The component does not open links, send reports, block contacts, or perform external actions.
- It uses the evidence already returned for the case; it does not invent a confidence score for each graph node.
- Missing evidence is described as missing rather than treated as proof of safety.

## Changed files
- Added `frontend/src/components/ManipulationGraph.jsx`
- Updated `frontend/src/pages/Review.jsx`
- Added this phase note

## Verification
Frontend build should be run in the project environment with `npm install` followed by `npm run build`. This packaging environment has not yet confirmed a successful frontend build.
