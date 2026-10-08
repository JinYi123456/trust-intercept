# Phase 12 — Privacy, Threat Model & Agent Security Hardening

## Goal
Treat every submitted message, URL, OCR result, QR payload, and transcript as attacker-controlled data.

## Threats covered
- Prompt injection inside scam messages.
- Tool abuse / SSRF through hostile URLs.
- Credential-bearing URLs.
- Attempts to make an agent reveal hidden policy or execute the attacker's instructions.
- Accidental trust of tool output as executable instruction.

## Controls
1. `backend/agent/security.py` marks case content as untrusted and detects common prompt-injection signals.
2. The LLM system boundary explicitly separates untrusted evidence from system/developer policy.
3. Optional sandbox recon is gated by human approval, HIGH risk, and a target URL policy that blocks localhost, private, link-local, reserved and credential-bearing targets.
4. Security-boundary findings are stored as auditable evidence.
5. Existing human approval remains the only path that records a completed defensive action.

## Design principle
The suspicious message is evidence, not authority.

A sentence such as `ignore previous instructions` inside an SMS must never become an instruction to TRUST//INTERCEPT.

## Limitations
Prompt-injection detection is intentionally not treated as a complete detector. The security boundary is the primary control; pattern matching is an observable warning layer. Production deployment should add network egress controls, URL sandboxing, rate limits, authentication and isolated worker processes.
