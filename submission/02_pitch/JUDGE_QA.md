# The 12 toughest judge questions — with honest answers

Keep every answer to two sentences. Concede real weaknesses; show the mitigation. Never defend a number we can't defend.

1. **"You quoted precision 0.82 on a 77-case benchmark you partly wrote yourselves. Why should we believe any of it?"**
   You shouldn't take it as an accuracy claim — it's a development signal, and the benchmark's value is that it's small, fully labelled, and every case carries a provenance tag (20 verbatim from UCI's SMS Spam Collection, 57 synthetic). It already caught a real bug in our rule library, and the roadmap to a credible claim is written down: labelled Malaysian-traffic data we're asking for today.

2. **"What if the LLM is prompt-injected by the scam message itself?"**
   The message is redacted and delivered to the model strictly as untrusted data, with a system instruction that case content can never change policy — and crucially, even a fully hijacked model can't do damage because no endpoint executes actions; only the human-approval gate writes anything. The LLM also only explains — the risk floor comes from deterministic rules the model can never lower.

3. **"How is this different from Google Safe Browsing or an SMS filter?"**
   Those blocklist known-bad URLs after they're weaponised, and say nothing at decision time about a message with no link yet. We intercept the decision: name the action the attacker wants, state what would prove legitimacy, and assign an independent-channel check — for zero-day wording the blocklists haven't seen.

4. **"Privacy: what actually leaves the device?"**
   IC, card numbers, phone numbers and OTPs are redacted on-device first; only redacted text and module JSON may reach a hosted LLM, and only if a key is configured — the full engine runs with zero hosted calls. Reputation lookups are opt-in and send only the URL, never the message, and originals are never stored.

5. **"Your false-positive rate is 21%. Why is that acceptable?"**
   It isn't acceptable for auto-blocking — which is precisely why the product never auto-blocks; the human sees the highlighted reason and can disagree in one tap, and that correction is logged and re-runs the pipeline. It's a floor to fix (the Malay keyword library and the card-notification allow-list are named fixes from our own failure table), not a feature.

6. **"The demo ran offline. Doesn't that mean the AI is doing nothing?"**
   In offline mode, correct — and that's the design: deterministic rules do detection, agents argue from real tool outputs, and hosted AI is an optional explanation layer capped at two calls per case. A scam-protection tool that dies without internet would fail exactly the people who need it most.

7. **"Why four agents? Isn't this one rule engine with costumes?"**
   The roles force contradictions into the open — Skeptic exists to argue the benign case even when Hunter's evidence looks damning, and the transcript is logged per case so you can audit who said what. The deterministic raise-only policy gives them teeth: prosecution can raise the risk, defence can never silence tool evidence.

8. **"How do you know your counterfactual verification actually works in the field?"**
   We don't yet — we know it's honest: the system marks the independent channel NOT CHECKED rather than fabricating confirmation, and logs whether evidence supports, contradicts or stays inconclusive. Field validation with real users is exactly what the pilot ask is for.

9. **"What stops a scammer from adapting to your keywords tomorrow?"**
   Individual keywords will always be a treadmill — that's why the product's core is not keywords but the decision-defence structure: urgency, credential requests, payment pressure and impersonation are behavioural patterns that survive rewording. And when a new wording beats the rules, the human approval gate means the failure mode is a slower decision, not a lost life savings.

10. **"Who is liable if your advice is wrong and someone loses money?"**
   The product only ever advises and never acts — no sending, blocking, or filing without the human's explicit click — and every verdict carries its evidence and uncertainty note so the human makes an informed choice. We'd position the pilot under the same terms as any advisory tool: recommendation, not guarantee, with full audit trail of what we showed the user.

11. **"Why would a bank or telco deploy this instead of building it themselves?"**
   The explainable decision-defence object — attack chain, counterfactual condition, independent verification task, audit hash — is the hard-won part, and it's provider-agnostic JSON their existing stack can call. Building the agent pipeline, the redaction boundary and the human-gate audit in-house is months; piloting ours is a week.

12. **"What's your moat once the idea is public?"**
   The moat compounds on two sides: the labelled Malaysian case library (every disagreement from real users becomes training and evaluation data) and the localisation depth — Macau scripts, PosLaju/J&T patterns, TNG freeze scams, LHDN/PDRM wording — which global vendors won't prioritise. Detection alone is a commodity; the decision-defence contract plus local data is the defensible pair.
