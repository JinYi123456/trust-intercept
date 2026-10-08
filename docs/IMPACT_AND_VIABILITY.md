# Impact & Viability (proposal one-pager)

## The problem we intercept

Scam losses in Malaysia are measured in billions of ringgit annually, and the attack is not on your wallet first — it is on your **next decision**. Victims do not lose money because they cannot spot fraud; they lose it because a message manufactures urgency at the exact moment they are distracted. Every existing tool answers *"is this a scam?"* with a probability and then goes silent at the moment of decision.

## Target users (who and why them)

1. **Seniors and their families** — the highest-loss demographic for Macau-scam and impersonation scripts. Our UI carries a Bahasa Malaysia/English toggle, plain-language verdicts ("Danger — likely a scam", not a risk score), and a caregiver escalation card that shares a fully redacted alert to a trusted family member. The human approval gate exists precisely for users who should never be auto-decided for.
2. **SME staff handling payments** — invoice-redirection and fake-MD-email scams hit finance staff. For them the product is a pre-payment check: paste the payment instruction, get the independent-verification task ("call the vendor on the number in your contract — not the one in this email") before the transfer leaves.
3. **Students and young workers** — the top targets for task/job scams ("pay RM50 registration"), e-wallet freeze phishing and prize-bait. They meet the product where the scam arrives: a browser extension and a phone app.

## Deployment paths (in the order we would ship)

1. **PWA (shipping today)** — installable, works offline in deterministic mode, no store approval. The demo path is live: submit → verdict → independent-verification task → human approval.
2. **Browser extension** — select any suspicious text anywhere and send it for analysis (the interaction model is already prototyped in the codebase). Zero-friction for email-based SME scams.
3. **Bank / telco API** — the same decision-defence engine behind an endpoint a bank can call before showing a "did you authorise this?" prompt, or a telco before delivering a known mule-account URL. The engine is provider-agnostic and returns explainable JSON, which is what regulated institutions need for audit.

## Why human approval beats auto-blocking (design, not marketing)

- **Auto-blocking at realistic precision punishes the wrong people.** On our benchmark (77 cases, deterministic mode) precision is 0.82 — one false alarm in five. A block button at that rate severs real deliveries, real banks, real landlords. An *advisory* card at that rate costs the user three seconds and gives them the reason.
- **The failure modes are different.** A classifier's mistake is invisible and final (message gone, sender blocked, payment frozen). Our mistakes are visible and reversible: the human sees the cues, the uncertainty note, and a one-tap "I disagree — re-check" that re-runs the pipeline with the correction logged.
- **Scammers adapt to classifiers faster than to humans.** Auto-block is an arms race the scammer optimises against (they A/B-test wording). A human-approval design trains a *decision habit* — verify through an independent channel — which survives the next template change. The awareness quiz tied to each real case reinforces exactly that habit.
- **Accountability is structural.** `action_taken` is written only by `POST /case/{id}/decision` — the only endpoint that can record a human action. Nothing is sent, blocked, or filed without an explicit click, and every decision is snapshotted in the audit log with the evidence hash.
- **It is the only safe design at our accuracy — and at any accuracy.** Even at 99% precision, auto-blocking one grandparent's genuine bank call is a harm we are not willing to cause. The gate is not a legal shield; it is the product.

## Unit economics

The engine runs fully deterministic at **0 hosted LLM calls** per case; hosted mode tops out at **2 calls per case** (plus 1 each for the optional report and quiz), with only redacted text leaving the device (see `EVALUATION_SUMMARY.md` §5–6). Marginal cost in the demo configuration (free/promo provider tiers) is approximately RM0 — the cost invariant we control is the call count, not volatile list prices.

## What we are NOT claiming

Our benchmark numbers (F1 0.771, FPR 0.214 — our benchmark, deterministic mode, 77 cases) are a development signal, not an accuracy claim on live traffic. The case set is small and partly synthetic; production claims would require labelled Malaysian-traffic data we do not have. The path to that evidence is specified in `EVALUATION_SUMMARY.md` §4.
