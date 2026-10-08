# TRUST//INTERCEPT — LLM Provider Strategy

TRUST//INTERCEPT supports hosted reasoning without making hosted inference the only safety path.

## Competition demo priority

`Gonka → Featherless → Gemini → deterministic local engine`

For the live HackAI demo, configure:

```text
LLM_PROVIDER=gonka
GONKA_API_KEY=<backend secret>
GONKA_MODEL=MiniMaxAI/MiniMax-M2.7
```

The browser never receives the provider key.

### GonkaRouter

Primary hosted reasoning provider for the competition demo. Best use:
- Evidence Arbiter
- Counterfactual Reality Check
- high-value scam-pattern explanation

### Featherless

Alternative hosted provider for model comparison or fallback when its promotional credits are available.

### Gemini

Fallback provider and multimodal/audio option. It can be used directly with `LLM_PROVIDER=gemini`.

### Offline deterministic engine

Recovery path when no hosted provider is available. It provides cue extraction, manipulation pressure, decision-defence scoring, false-positive checks, safe verification guidance and the human approval gate.

## Cost-control rule

A normal case should not call a hosted model for every agent. Target: **0–2 hosted LLM calls per case**.

## Secrets

Never commit real keys. Store them only on the backend host or local `.env`:

```text
GONKA_API_KEY=
FEATHERLESS_API_KEY=
GEMINI_API_KEY=
```
