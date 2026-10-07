# TRUST//INTERCEPT Architecture

## 1. Product identity

**Team:** Aegis Signal Lab  
**Product:** TRUST//INTERCEPT  
**Repository:** `trust-intercept`  
**Tagline:** INTERCEPT THE DECISION.

## 2. Agentic pipeline

1. Trust Gateway — accepts text, image, QR, URL, document or audio.
2. Local Normaliser — OCR/QR extraction and PII redaction before model access.
3. Evidence Graph — converts all observations into a common evidence object.
4. Agent Router — selects only the tools required for the case.
5. Hunter Agent — searches for attack indicators and infrastructure evidence.
6. Skeptic Agent — actively searches for benign explanations and false positives.
7. Verifier Agent — identifies what independent evidence could overturn the current assessment.
8. Evidence Arbiter — synthesises only supported claims and exposes uncertainty.
9. Manipulation Graph — maps the attacker's intended decision chain.
10. Decision Defence — proposes VERIFY, PAUSE or REPORT, never autonomous execution.
11. Human Approval Gate — the person authorises the next action.
12. Immunity Coach — turns the incident into an adaptive training scenario.

## 3. Design principle

The system is not a binary scam classifier. It is a **decision-defence system**.

## 4. Model policy

Default: deterministic local engine.  
Optional: Gemini free-tier API.  
No paid model is required for the baseline demo.

## 5. Safety

- Never open a suspicious destination merely to inspect it in the user's browser.
- Never use contact details supplied by a suspicious message as the verification channel.
- Never claim voice analysis proves a deepfake.
- Never auto-block or auto-report a real person or account.
- Always expose uncertainty and “what we did not check”.

## 6. Free-first LLM budget

The adversarial roles are deterministic. If Gemini is configured, the evidence arena uses at most one optional arbitration call and the final synthesis uses one call. The full application remains functional with zero hosted calls.
