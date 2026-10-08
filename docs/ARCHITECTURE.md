# TRUST//INTERCEPT Architecture

## 1. Product identity

**Team:** Aegis Signal Lab  
**Product:** TRUST//INTERCEPT  
**Repository:** `trust-intercept`  
**Tagline:** INTERCEPT THE DECISION.

## 2. Deployment architecture

For the competition demo, the intended deployment is:

```text
Vercel
  React/Vite frontend
        │ HTTPS
        ▼
FastAPI backend
        │
        ├── deterministic evidence/tool layer
        ├── optional hosted LLM provider
        ├── optional reputation services
        └── persistent case/audit storage
```

The frontend receives only `VITE_API_BASE_URL`. Provider API keys stay on the backend host and are never bundled into the browser build.

## 3. Agentic pipeline

1. Trust Gateway — accepts text, image, QR, URL, document or audio.
2. Local Normaliser — OCR/QR extraction and PII redaction before model access.
3. Evidence Graph — converts observations into a common evidence object.
4. Agent Router — selects only the tools required for the case.
5. Hunter Agent — searches for attack indicators and infrastructure evidence.
6. Skeptic Agent — actively searches for benign explanations and false positives.
7. Verifier Agent — identifies what independent evidence could overturn the current assessment.
8. Evidence Arbiter — synthesises only supported claims and exposes uncertainty.
9. Manipulation Graph — maps the attacker's intended decision chain.
10. Decision Defence — proposes VERIFY, PAUSE or REPORT, never autonomous execution.
11. Human Approval Gate — the person authorises the next action.
12. Immunity Coach — turns the incident into an adaptive training scenario.

## 4. Design principle

The system is not a binary scam classifier. It is a **decision-defence system**.

## 5. Model policy

**Competition demo:** recommended hosted provider is Gonka via `LLM_PROVIDER=gonka` and a backend-only `GONKA_API_KEY`. Featherless and Gemini remain supported alternatives/fallbacks.  
**Recovery:** deterministic local mode remains available with `LLM_PROVIDER=none`.

## 6. Safety

- Never open a suspicious destination merely to inspect it in the user's browser.
- Never use contact details supplied by a suspicious message as the verification channel.
- Never claim voice analysis proves a deepfake.
- Never auto-block or auto-report a real person or account.
- Always expose uncertainty and “what we did not check”.
- Treat all user-supplied message, OCR, QR, URL and transcript content as untrusted data.

## 7. LLM budget

Hunter, Skeptic and Verifier are deterministic/local-first. Hosted reasoning is reserved for high-value synthesis. Target: **0–2 hosted LLM calls per case**.
