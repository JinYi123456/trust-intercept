# TRUST//INTERCEPT — LLM Provider Strategy

TRUST//INTERCEPT is designed to remain functional without any hosted LLM. Hosted models improve synthesis quality, but they are never the only path to a working demo.

## Priority order

`Gonka → Featherless → Gemini → deterministic local engine`

The order is intentional: use promotional/free credits first, then Gemini's free tier, then fall back locally.

### GonkaRouter

Use for agentic text synthesis and adversarial reasoning when free monthly tokens are available. Gonka exposes an Anthropic-compatible `/v1/messages` API and its current free tier provides at least 1M tokens/month on eligible accounts.

Best use in this project:
- Evidence Arbiter
- Counterfactual Reality Check
- Scam-pattern explanation

Do not use it for every tiny rule. Local agents should do deterministic extraction first.

### Featherless

Use for open-weight model experimentation and benchmark comparisons when the user's redeemed promotional credits are available. Featherless exposes an OpenAI-compatible API and a large catalogue of open-weight models.

Best use in this project:
- Alternative Arbiter model
- Model comparison in Evaluation Lab
- Stress-testing explanations

The application never assumes Featherless credits exist; an empty key simply skips the provider.

### Gemini

Use as the resilient free-tier hosted fallback, and for multimodal/audio capabilities already supported by the project.

Best use in this project:
- Text synthesis fallback
- Multimodal/audio analysis
- Demo-day backup provider

### Offline deterministic engine

Always available. It provides:
- cue extraction
- manipulation pressure
- decision-defence scoring
- false-positive checks
- safe verification guidance
- human approval gate

This is the final reliability layer.

## Cost-control rule

A normal case should not call a hosted model for every agent. Hunter, Skeptic, Verifier and most evidence extraction are deterministic/local. A hosted model is used only for high-value synthesis.

Target: **0–2 hosted LLM calls per case**.

## Secrets

Never commit real keys. Put them in `.env` locally or in deployment secrets.

```text
GONKA_API_KEY=
FEATHERLESS_API_KEY=
GEMINI_API_KEY=
```
