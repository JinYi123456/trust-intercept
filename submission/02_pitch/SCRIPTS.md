# Pitch scripts — 4-minute main + 90-second backup

## Main script — 4:00 (word for word)

**[0:00–0:35] Slide 1 — Problem**

"Aunty Lim was expecting a parcel. Her phone buzzed: *PosLaju — your parcel is held. Pay RM3.90 delivery fee within 24 hours or it goes back.* She typed her name. Then her IC. Then her card number. Then the OTP. The message wasn't from PosLaju. Nothing stopped it, because nothing explained it. The one thing that message never showed her was its own playbook. We built TRUST//INTERCEPT to show that playbook, in plain words, before the money leaves."

**[0:35–1:05] Slide 2 — User**

"Who holds this phone? Three people. A senior whose children worry about her — our app speaks English and Bahasa Malaysia, in plain words, and can one-tap an alert to a trusted family member. An SME finance officer staring at a payment email from 'the boss' — our pre-payment check says: call the vendor on the number in your contract, not this email. And a student getting 'you won an iPhone, just pay RM18 postage.' Different people, same weapon: a manufactured decision."

**[1:05–1:35] Slide 3 — Insight**

"Here's our insight. Scams don't steal money first — they control your next decision. Every scam detector on the market answers 'is this a scam?' and then goes silent at the exact moment a human has to act. We flip the question: what is this message trying to make you do? What would have to be true for it to be legitimate? And how do you check that without the scammer's help? A probability can't answer that. A checklist can."

**[1:35–3:05] Slide 4 — Live demo** *(click through per RUN_OF_SHOW.md; talk while it runs)*

"Let me show you, live. *(paste)* Here's a real parcel-fee scam. The verdict took seconds: Danger — likely a scam, high confidence — and look, it shows its work: urgency, OTP request, disguised short link, card details — each one highlighted in the exact sentence where it appears. Now the part nobody else shows: 'what could make us wrong.' And the safest next step: do not use any link or number from this message — check the courier's official app, or call the bank using the number on your card. The system did not open that link. It did not verify it for her. It hands the verification task to the human, honestly marked 'not checked,' because pretending to verify would be the real scam. Last step is hers: she approves the warning. One click. Logged, hashed, done. Nothing happened without her. And if the internet dies right now — the whole engine still runs offline, with zero AI calls."

**[3:05–3:35] Slide 5 — Agent workflow**

"Under the hood, four agents investigate. Hunter builds the attack case. Skeptic argues the innocent explanation — our protection against false alarms. Verifier names the evidence that could overturn everything. Arbiter settles it on the record. One rule makes this trustworthy: the debate can raise the risk, but it can never lower the evidence floor. And the output is not a score — it's a claim, plus the independent channel that proves or refutes it, plus who has to do the checking: you."

**[3:35–4:00] Slides 6–8 — Safety, evidence, ask**

"Safety, in one line: nothing is sent, blocked, or filed without an explicit human click — one endpoint writes it, every decision is hashed and auditable, and personal data is redacted on-device before anything leaves. Our numbers, honestly: on our 77-case benchmark, precision 0.82 — meaning one false alarm in five — which is exactly why we never auto-block. The human sees the reason and can disagree. What we need: one bank or telco for a pilot, and labelled Malaysian scam data. Don't just detect the scam — intercept the decision."

---

## Backup script — 1:30 (demo failed / offline mode)

Say this calmly. The failure *is* the demo.

"[0:00–0:20] Judges, sometimes the internet fails — which is the perfect time to show you why this product works for a grandmother in a village with one bar of signal. We built two engines. The AI engine is optional. The deterministic engine runs entirely on this laptop. Watch.

[0:20–1:00] *(paste the scam, click through)* Verdict: high risk. Red flags: urgency, OTP, disguised link — highlighted in the sentence. What could make us wrong: listed. Safest next step: call the bank on the number on your card — not any number in this message. Zero network calls. Zero hosted AI. This is not a degraded mode; it's the safety net your bank app doesn't have.

[1:00–1:30] When the AI is available, it explains and challenges — two calls per case, redacted text only. When it isn't, the checklist still protects the decision. That was the design principle from day one: the human and the checklist come first, the AI is a bonus. Don't just detect the scam — intercept the decision."
