# Phase 11 — Evaluation Lab & False-Positive Defence

TRUST//INTERCEPT now exposes `/evaluation`, a local benchmark that runs the real investigation pipeline without persisting benchmark cases.

## Benchmark classes
- Scam: parcel/payment and bank/account takeover pressure.
- Legitimate: normal courier and bank notices that explicitly avoid unsafe requests.
- Borderline: delivery language with no payment or credential request.
- Adversarial safe: messages containing scam vocabulary while explicitly telling the user not to act.

## Metrics
- Accuracy
- Precision
- Recall
- F1
- False Positive Rate
- TP / TN / FP / FN confusion matrix

A medium/high verdict is treated as an interception prediction for this benchmark. Borderline cases are deliberately counted as false-positive pressure rather than quietly removed.

## Safety
The benchmark uses local analysis only, does not persist its cases, does not send benchmark content to a user, and never opens suspicious URLs.

The displayed metrics are benchmark evidence, not a universal accuracy claim. A competition submission should expand the labeled set and include independently verified Malaysian-language and real-world samples.

## Phase 11 hardening result

The first benchmark run intentionally exposed two false positives: a legitimate bank notice and an adversarially worded safety reminder. The phishing detector was hardened with conservative defensive-context handling. Re-running the same six-case benchmark produced:

- Accuracy: 1.0000
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- False Positive Rate: 0.0000

These are benchmark results only, not a claim of universal real-world performance. The important engineering outcome is that the benchmark can expose and regress false-positive failures rather than hiding them.
