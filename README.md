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

TRUST//INTERCEPT asks a more useful question:

**“What is this message trying to make you do, what evidence supports that, what could make us wrong, and what is the safest next decision?”**

## Core loop

`INTAKE → NORMALISE → ROUTE → HUNT → SKEPTIC → VERIFY → ARBITRATE → INTERCEPT → HUMAN APPROVAL → VERIFY / PAUSE / REPORT → LEARN`

## Privacy-first runtime

- PII is redacted before LLM analysis.
- Local deterministic analysis works with **no API key**.
- Gemini is the optional cloud reasoning provider.
- No real contact is blocked, reported, or contacted automatically.
- Human approval is required before consequential actions.

## Repository hygiene

Generated environments, secrets, local databases, build outputs, caches and packaged source archives are intentionally excluded from the repository.

## Status

This repository is the clean TRUST//INTERCEPT rebuild of the legacy prototype. The next phases replace the old dashboard flow with the Interception Room, Evidence Graph, Adversarial Evidence Arena, Counterfactual Verification and Decision Safety metrics.


## LLM provider strategy

TRUST//INTERCEPT is provider-agnostic. With `LLM_PROVIDER=auto`, the backend tries **Gonka → Featherless → Gemini**, then keeps running on the deterministic local engine if no hosted provider is available. This lets the project use redeemed promotional/free credits without making the competition demo depend on a paid service. See `docs/LLM_PROVIDER_STRATEGY.md`.

**Target:** 0–2 hosted LLM calls per case. Deterministic Hunter/Skeptic/Verifier logic runs locally; hosted inference is reserved for high-value synthesis.
