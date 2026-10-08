# Evaluation Lab — Summary (Benchmark v2)

**All numbers in this document are from OUR BENCHMARK unless explicitly attributed to a dataset or marked as an estimate.** They are a local sanity check, not a product accuracy claim on live traffic.

---

## 1. What the benchmark is

The Evaluation Lab runs the **real investigation pipeline** (normalisation → phishing rules → link safety → psych radar → Red/Blue debate → defence → verdict) over a fixed case set, without persisting cases or opening any URL.

**Configuration of the reported run:** deterministic engine (`LLM_PROVIDER=none`), outbound lookups disabled (`ALLOW_OUTBOUND_LOOKUPS=false`), redaction active. Predicted "interception" = risk score Medium or High. **Borderline cases predicted positive count as false-positive pressure** (documented convention).

## 2. Case set — 77 cases, fully attributed

| Source | Cases | Description |
|---|---|---|
| **SMS Spam Collection v.1** (UCI ML Repository id 228; Almeida et al., ACM DOCENG'11) | 20 | 10 spam + 10 ham messages used **verbatim** with the dataset's own ground-truth labels. Copyright remains with the dataset authors (see its license/disclaimer file). |
| **Synthetic** (team-written for this benchmark) | 57 | Cases reflecting publicly reported Malaysian scam patterns — parcel fees (PosLaju/J&T), Macau scam (PDRM/immigration scripts), e-wallet freeze (TNG/Boost/ShopeePay), LHDN tax-refund impersonation, Maybank phishing — plus legitimate notices, borderline messages and adversarial wording. **Not real victim messages.** |
| **CIC-Trap4Phish** (UNB CIC) | 0 | **Not integrated.** The dataset page returned HTTP 404 when this benchmark was built, and access normally requires a request to the CIC team. Documented as a gap — not claimed as a source. |

Composition: **37 scam · 28 legit · 12 borderline** across channels **SMS (69) · email (3) · URL (3) · QR (2)** and languages **English (58) · Manglish (10) · Bahasa Malaysia (9)**.

Full case list with per-case provenance tags: [`backend/agent/benchmark_cases.py`](../backend/agent/benchmark_cases.py). Machine-readable breakdown is served live by `GET /evaluation`.

## 3. Results (our benchmark — deterministic mode)

| Metric | Value (our benchmark) |
|---|---|
| Accuracy | **0.675** |
| Precision | **0.818** |
| Recall | **0.730** |
| F1 | **0.771** |
| False-positive rate (legit only) | **0.214** |

Confusion matrix: TP 27 · TN 25 · **FP 6 · FN 10**.

### By language (our benchmark)

| Language | Cases | Recall | FPR | Note |
|---|---|---|---|---|
| English | 58 | 0.692 | 0.286 | misses UK dataset-era premium-rate spam; keyword traps on legit card notifications |
| Manglish | 10 | 1.000 | 0.000 | small sample; 4 scam cases carry English scam keywords |
| Bahasa Malaysia | 9 | 0.714 | 0.000 | 2 Malay Macau-scam scripts missed — known multilingual gap |

### By channel (our benchmark)

| Channel | Cases | Accuracy | Note |
|---|---|---|---|
| SMS | 69 | 0.652 | main channel; carries both the misses and the false positives |
| email | 3 | 1.000 | 3 cases — anecdotal, not statistically meaningful |
| URL | 3 | 1.000 | 3 cases — anecdotal |
| QR | 2 | 0.500 | the QR scam payload was one of the false negatives |

## 4. Failure cases — shown honestly (16 of 77)

**False negatives (10) — scams we missed:**

| Case | Why it failed (our benchmark) |
|---|---|
| `uci_sp_03/04/06/07/08/10` (6×) | UK dataset-era premium-rate spam ("txt to 87066", ringtone subscriptions). Our cue library targets Malaysian patterns; UK short-code grammar is out of scope. |
| `syn_scam_task` | Job-task scam asking a "registration fee" — no urgency/OTP/link keywords fired. |
| `syn_ms_macau` | Malay Macau-scam script ("kes jenayah dan waran tangkap"). The Malay keyword library does not exist yet — the single biggest known gap. |
| `syn_qr_payment` | QR payload pointed to an unknown domain that is neither a shortener nor IP/HTTP — needs domain-age/reputation (disabled offline). |
| `adv_ms_meta` | Malay "this is not a scam" meta-manipulation; same multilingual gap. |

**False positives (6) — legitimate/borderline flagged (FP pressure):**

| Case | Why it failed (our benchmark) |
|---|---|
| `syn_lg_card` (legit → **high**) | "Your new debit card has been mailed… activate in the app" matched the card-details rule. **A real rule-library bug** — highest-priority fix. |
| `adv_otp_negative` (legit → high) | The OTP public-awareness message *mentions* OTP/PIN — classic keyword-trap failure. |
| `uci_hm_04` (ham → medium) | "I need AXIS BANK account no" — a person asking a friend, read as a credential request. |
| `bln_refund`, `bln_bank_confirm`, `bln_roadtax` | Borderline notifications (refund notice, bank fraud-confirmation, JPJ expiry) flagged medium/high. Partly by design (borderline = FP pressure), partly keyword over-triggering. |

**Reading the numbers honestly:** precision 0.82 means roughly 1 in 5 interceptions would be a false alarm on this mix — for a *human-gated advisory* tool this is uncomfortable but survivable (the human sees why and can disagree); for an *auto-blocking* tool it would be disqualifying. This is a core argument for the human-approval design (see `IMPACT_AND_VIABILITY.md`).

**Roadmap from failures (each maps to a named fix):** Malay/Manglish keyword library (fixes 3 FN), brand-impersonation allow-list for card/statement notifications (fixes the worst FP), URL short-code + premium-number rules for non-MY spam, QR domain reputation path (requires hosted lookups).

## 5. Cost per case (our benchmark — code-inspected call counting, no invented prices)

| Component | Hosted LLM calls |
|---|---|
| Phishing cue explanation | 0–1 per case |
| Debate judge (1 optional arbitration call) | 0–1 per case |
| **Max per submitted case** | **2** |
| Report bundle (user-requested) | +1 |
| Coach quiz (user-requested) | +1 |
| Deterministic engine alone | **0** |

Token budget per call (from configuration, our benchmark): output capped at 1,400 tokens; prompt inputs carry only the **redacted** text (capped at ~3–4k characters in code) plus module JSON.

**RM cost = calls × your provider's list price.** The demo path uses free/promo tiers (Gonka/Featherless promo pools, Gemini free tier), so marginal cost in the configured demo configuration is approximately RM0. We deliberately do not quote provider prices — they change; the call count is the invariant we control.

## 6. Privacy statement (what leaves the device)

- **Redacted before anything happens:** IC/NRIC, phone numbers, card numbers, emails, OTPs are replaced with placeholders (`[REDACTED_IC_NRIC_1]`, …) by the local PII-redaction module before analysis. The original text is never stored by the backend.
- **What may leave the device (only if a hosted LLM key is configured):** the **redacted** text and module JSON, sent to the LLM provider for explanation/synthesis. The PII map never leaves the process.
- **What never leaves:** the unredacted original, the PII map, any database content. The local SQLite store contains redacted cases only.
- **Reputation lookups (opt-in, `ALLOW_OUTBOUND_LOOKUPS`):** send only the URL/domain — never the message body. Off by default in offline demo mode.
- **Suspicious destinations are never opened** — links are only inspected, and the redirect walker never downloads page bodies.
- **Benchmark cases are never persisted** to the database.

## 7. How to reproduce

```bash
# backend (deterministic, offline)
DB_PATH=/tmp/ti_eval.db LLM_PROVIDER=none ALLOW_OUTBOUND_LOOKUPS=false \
  PYTHONPATH=. uvicorn backend.main:app --port 8001
# then: GET http://127.0.0.1:8001/evaluation  (returns everything above, machine-readable)
```

`GET /evaluation` returns the full metrics, per-language/channel/source breakdowns, the complete failure list with the exact case text, and the cost estimate — every run, no screenshots needed.
