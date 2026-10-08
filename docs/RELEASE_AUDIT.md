# TRUST//INTERCEPT — Release Audit

## Scope
Final red-team and release-hygiene audit for the Phase 16 release candidate and live-demo deployment.

## Security checks
- Private operator manual is gitignored and must never be committed to the public repository.
- No live API keys or provider secrets are present in the release candidate.
- Suspicious/private-network URLs are blocked by the outbound tool policy.
- Untrusted message content is treated as evidence, not authority.
- Case replay is read-only and does not re-run external investigation.
- Human approval remains required for consequential defensive actions.

## Functional validation
- Backend regression: 47/47 tests passed, including the 8-test end-to-end demo smoke suite (scam→approval, legitimate→no-false-alarm, offline fallback).
- Python compilation: passed.
- Evaluation benchmark v2 (77 cases, provenance-tagged) remains part of the regression suite; metrics and all 16 failure cases are published in `EVALUATION_SUMMARY.md`.
- Frontend production build: verified (`npm install && npm run build`, exit 0).

## Release limitations
- Benchmark figures (precision 0.818, FPR 0.214 — our benchmark, deterministic mode) are evidence for the included dataset only; they are not real-world detection claims, and the false-positive rate is the documented reason the product requires human approval instead of auto-blocking.
- The Malay/Manglish keyword library is a known gap (2 Malay Macau-scam cases missed on our benchmark); it is the first item on the post-pitch roadmap.
- The competition demo is intended to use a real hosted LLM provider on the backend. Offline mode remains the safety floor and recovery path.

## Public-release rule
Before pushing to a public repository, verify `git status` does not list `PRIVATE_OPERATOR_MANUAL.md`, `.env`, databases, logs, caches, or credentials.
