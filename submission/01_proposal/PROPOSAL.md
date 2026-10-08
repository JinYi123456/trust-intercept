# TRUST//INTERCEPT — Proposal

## Team
Aegis Signal Lab

## Track
HackAI Malaysia 2026 — Track 03: Scam Defence & Awareness

## 1. Problem
Scams increasingly manipulate people into making a fast decision: click a link, pay money, disclose an OTP, install software, or trust an impersonator. A binary scam score does not explain the manipulation or give the user a safe path forward.

## 2. Solution
TRUST//INTERCEPT is an agentic decision-defence system. It converts suspicious text, URLs, QR codes, screenshots, documents and voice evidence into a common evidence model, then uses Hunter, Skeptic and Verifier roles to challenge the case before an Evidence Arbiter forms a conclusion.

The product asks four questions:
1. What is the message trying to make the person do?
2. What evidence supports that interpretation?
3. What evidence could prove us wrong?
4. What is the safest independent next step?

## 3. Agentic Workflow
INTAKE → NORMALISE → ROUTE → HUNT → SKEPTIC → VERIFY → ARBITRATE → INTERCEPT → HUMAN APPROVAL → VERIFY / PAUSE / REPORT → LEARN.

Suspicious content remains untrusted data throughout the workflow. It cannot redefine agent instructions or trigger consequential actions.

## 4. Differentiation
The distinctive design is the combination of adversarial evidence review, manipulation mapping, counterfactual verification, a human approval gate, replayable provenance and adaptive scam-immunity training. The goal is not merely to classify a scam, but to defend the user's next decision.

## 5. Safety and Privacy
PII is redacted before hosted reasoning. The competition demo uses hosted reasoning through a server-side provider key; deterministic local analysis remains available as a recovery mode without API keys. Suspicious destinations are not opened in the user's browser. The system does not automatically contact, block or report people. Consequential actions require human approval.

## 6. Evaluation
The built-in Evaluation Lab covers scam, legitimate, borderline and adversarial cases and reports accuracy, precision, recall, F1 and false-positive rate. Phase 11's benchmark currently passes its maintained test set with 100% accuracy, 100% precision, 100% recall, 100% F1 and 0% false-positive rate. These figures describe the maintained benchmark only and are not claimed as real-world detection rates.

## 7. Demonstration
The primary three-minute scenario is a parcel-delivery scam. The user submits the message, sees the requested action and manipulation chain, watches Hunter/Skeptic/Verifier challenge the evidence, receives an independent verification path, approves a safe next step, then opens the Evidence Passport and Case Replay. The final step is a short immunity challenge showing how the incident becomes future awareness training.

## 8. Expected Impact
TRUST//INTERCEPT aims to reduce impulsive scam decisions by making manipulation visible, verification independent and consequential action human-controlled. It is designed for everyday users while remaining auditable enough for security teams, educators and researchers.

## 9. Limitations
The system cannot guarantee scam detection. Reputation, domain and external intelligence may be unavailable. Voice analysis does not prove a deepfake. Independent verification may remain inconclusive. The safest output can therefore be PAUSE rather than a forced verdict.
