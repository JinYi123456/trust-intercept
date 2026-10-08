# TRUST//INTERCEPT

**INTERCEPT THE DECISION.**

An agentic scam-defence platform that investigates suspicious messages, links, QR codes, documents and voice evidence — then protects the decision *before* the user acts.

> Scams do not need to steal your money first. They need to control your next decision.

## Team

**Aegis Signal Lab**

## Hackathon

HackAI Malaysia 2026 — Track 03: Scam Defence & Awareness

## Product thesis

Traditional scam detection asks: **“Is this a scam?”**

TRUST//INTERCEPT asks:

**“What is this message trying to make you do, what evidence supports that, what could make us wrong, and what is the safest next decision?”**

## Core loop

`INTAKE → NORMALISE → ROUTE → HUNT → SKEPTIC → VERIFY → ARBITRATE → INTERCEPT → HUMAN APPROVAL → VERIFY / PAUSE / REPORT → LEARN`

## Core product capabilities

- Multi-modal intake: text, URL, screenshot/QR and audio.
- PII redaction before hosted reasoning in the live demo; the deterministic local engine remains available as a recovery path.
- Evidence-first Hunter / Skeptic / Verifier challenge.
- Manipulation Graph™ for attacker intent and requested action.
- Counterfactual verification through an independent channel.
- Human approval gate before consequential action.
- Evidence Passport and Case Replay / provenance.
- Adaptive scam-immunity training.
- Evaluation Lab with legitimate, borderline and adversarial cases.
- Security Boundary against prompt injection, SSRF-style targets and untrusted tool output.
- Offline deterministic mode when hosted providers or network access are unavailable.

## Runtime safety

Suspicious content is treated as **untrusted data, not instructions**. The application does not automatically contact a sender, submit a report, open a suspicious destination, or execute an action on the user's behalf.

## Privacy-first runtime

- PII is redacted before LLM analysis.
- Local deterministic analysis works with **no API key**.
- Hosted reasoning is optional and provider-agnostic.
- No real contact is blocked, reported, or contacted automatically.
- Human approval is required before consequential actions.

## Development

Backend tests:

```bash
PYTHONPATH=. pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

Deployment uses a Vercel-hosted frontend plus a separately hosted FastAPI backend. The competition demo is intended to use a real hosted LLM API key on the backend; offline mode remains the recovery path. See `deployment/README.md` and `.env.example`.

## Repository hygiene

Generated environments, secrets, local databases, build outputs, caches and packaged source archives are intentionally excluded from the repository.

Competition-only materials belong under `submission/`; they are not product screens.

## Release readiness

Phase 16 is the release-candidate audit stage. Before submission, run the final checklist covering backend tests, frontend production build, live API-key demo, offline recovery path, secret scan and the three-minute demo smoke path. See `docs/RELEASE_AUDIT.md` and `submission/FINAL_SUBMISSION_CHECKLIST.md`.

## LLM provider strategy

TRUST//INTERCEPT is provider-agnostic. For the competition demo, configure `LLM_PROVIDER=gonka` and store `GONKA_API_KEY` only on the FastAPI backend. For resilience, `auto` can try **Gonka → Featherless → Gemini** and then fall back to the deterministic local engine. Hosted inference is reserved for high-value synthesis.

**Target:** 0–2 hosted LLM calls per case.
