# TRUST//INTERCEPT — Pitch Deck (8 slides)

**Aegis Signal Lab · HackAI Malaysia 2026 · Track 03: Scam Defence & Awareness**

> Delivery notes: one idea per slide. Say the sentence in **bold** out loud. Everything else is on screen, not in your mouth. Every number is tagged — never say one without its tag.

---

## Slide 1 — Problem: "RM3.90"

**"Aunty Lim was expecting a parcel. One SMS said: pay RM3.90 delivery fee, or your parcel goes back."**

*(Screen: the actual PosLaju scam SMS on the left, the "what it wanted her to do" panel on the right: pay, enter IC, enter card, enter OTP.)*

- This exact pattern — courier fee + fake urgency + bank details — is one of the most reported scam types in Malaysia.
- She was 3 minutes and one click away from losing much more than RM3.90.
- Nobody showed her the scam's playbook before she had to decide.

## Slide 2 — User

**"We built this for the person holding the phone with one hand and a credit card in the other."**

*(Screen: three user cards — Senior + caregiver / SME finance staff / Student.)*

- **Seniors & families**: Macau-scam and impersonation scripts; BM/English toggle, plain words, one-tap alert to a trusted family member.
- **SME staff**: fake invoice and boss-impersonation emails; a pre-payment check before money leaves.
- **Students**: task-job scams ("pay RM50 to start work"), e-wallet freeze phishing, prize bait.

## Slide 3 — Insight

**"Scams don't steal money first. They control your next decision."**

- Detection asks: *Is this a scam?* — then stops, exactly where it matters.
- Decision defence asks: *What is this message trying to make you do? What would prove it's real? How do you check without the scammer's help?*
- We turn the question the scammer controls into a checklist the user controls.

## Slide 4 — Live demo

**"Watch the machine hand the decision back to her."**

*(Screen: the app. 90 seconds. Paste the scam → verdict → red flags → "what could make us wrong" → "call the bank, not the number in the message" → human approves.)*

- Real pipeline, real evidence trail, nothing pre-recorded.
- If the network dies: the whole thing still runs on the deterministic engine — offline is a feature, not a fallback story. *(Backup script: SCRIPTS.md.)*

## Slide 5 — Agent workflow (one diagram)

**"Four agents investigate. One human decides."**

*(Screen: one diagram — INTAKE → HUNTER / SKEPTIC / VERIFIER → ARBITER → decision-defence plan → counterfactual verification task → HUMAN APPROVAL.)*

- **Hunter** builds the attack case from the evidence. **Skeptic** argues the benign explanation. **Verifier** names what independent evidence could overturn the verdict. **Arbiter** resolves it on the record.
- Rule: the debate can **raise** the risk above the evidence floor — it can **never lower it**.
- Output is not a score. It is a claim ("this payment is legitimate") plus the exact independent channel that would prove or refute it — honestly marked NOT CHECKED until the user does it.

## Slide 6 — Safety and human approval

**"Nothing is sent, blocked, or filed without an explicit human click."**

- `action_taken` is written by exactly one endpoint — the human approval gate — and every decision is snapshotted with an evidence hash.
- Suspicious links are **never opened**: redirects are inspected hop-by-hop without downloading page bodies; suspicious content is treated as untrusted data, never as instructions.
- Privacy: IC, card numbers, phones and OTPs are redacted **on-device** before anything else happens; only redacted text can ever reach a hosted LLM; the engine also runs fully offline with zero hosted calls.

## Slide 7 — Evidence and honest limitations

**"Here are our real numbers, including the ones we don't like."**

*(Screen: the /evaluation failure table, live.)*

- Our benchmark: **77 cases** — 20 verbatim from the SMS Spam Collection (UCI), 57 synthetic, tagged per case.
- Deterministic mode: precision **0.818**, recall **0.730**, F1 **0.771**, false-positive rate **0.214** — *our benchmark, not a product claim.*
- We show every failure: 6 UK dataset-era premium-rate spam missed, the Malay keyword gap, a rule-library bug we found through this benchmark and are fixing.
- One in five false alarms is why we **don't auto-block** — a human sees the reason and can disagree in one tap.

## Slide 8 — Ask / next steps

**"Help us put the decision back where it belongs."**

- **Ask:** pilot partners — one bank or telco willing to test the decision-defence API on real (redacted) traffic, plus mentorship on financial-institution compliance.
- **Next 90 days:** Malay/Manglish keyword library (our benchmark shows it fixes the biggest failure class), fix the card-notification false positive, pilot the browser extension.
- **The ask behind the ask:** labelled Malaysian scam data to turn "our benchmark" into a real evaluation.

**Closing line:** *Don't just detect the scam. Intercept the decision.*
