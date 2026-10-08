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
- Backend regression: 39/39 tests passed.
- Python compilation: passed.
- Evaluation benchmark remains part of the regression suite.

## Release limitations
- Frontend production build must be verified on the developer machine with `npm install && npm run build` because the isolated build environment may not complete dependency installation.
- The benchmark result is evidence for the included dataset only; it is not a claim of real-world perfect detection.
- The competition demo is intended to use a real hosted LLM provider on the backend. Offline mode remains the safety floor and recovery path.

## Public-release rule
Before pushing to a public repository, verify `git status` does not list `PRIVATE_OPERATOR_MANUAL.md`, `.env`, databases, logs, caches, or credentials.
