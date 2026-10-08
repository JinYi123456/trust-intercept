# Demo run-of-show — 90 seconds inside the 4-minute pitch

**Before the pitch (T-10 minutes):**
1. `python run_dev.py` → backend on 8001+ and frontend on 5173+ (script auto-picks ports and writes `VITE_API_BASE_URL`).
2. Check `GET /health` → `"status": "ok"`, and the startup banner shows which LLM mode is live.
3. Pre-paste the PosLaju scam SMS into a scratch notepad (the exact text from `SUBMIT` sample button, so no typing errors on stage).
4. Browser at 100% zoom, only two tabs (app + scratch pad), notifications off.
5. Decide the trigger: if the app hasn't responded within 10 seconds at any step, say the backup line and switch to `SCRIPTS.md` — do not debug on stage.

| Time | What you say (cue from SCRIPTS.md) | Exact clicks |
|---|---|---|
| 1:35 | "Let me show you, live." | Click into the message box on `/` (Submit screen). |
| 1:40 | "…a real parcel-fee scam." | Paste the SMS → click **⚡ INVESTIGATE**. |
| 1:45–2:05 | "Verdict took seconds… shows its work…" | On `/case/…/review`: point at the verdict banner (⛔), then each highlighted cue (urgency → OTP → short link → card). |
| 2:05–2:25 | "Now the part nobody else shows…" | Point at the **🤔 What could make us wrong** card, then the **🧭 Safest next step** card (independent sources + 🇲🇾 NSRC 997 line). |
| 2:25–2:45 | "It hands the verification to the human…" | Click **Details ▼** once to show the highlighted message underneath (proves highlighting is real, then close it again). |
| 2:45–3:00 | "Last step is hers." | Open **Other options ▼** is NOT needed — click the primary **BLOCK / WARN** button → cooling-off barrier may appear: let it count 3 seconds, then **CONTINUE**. |
| 3:00–3:05 | "Logged, hashed, done." | Point at the gold confirmation banner; keep moving. |
| 3:05 | "Under the hood…" | Leave the review screen as-is; advance to Slide 5. |

**If anything hangs (>10s):** say — *"and sometimes the internet fails, which is exactly who this is for"* — switch to the 90-second backup script, and if the UI is dead, show the terminal: `curl localhost:8001/evaluation | head -40` proves the engine runs with zero network.

**Do NOT do on stage:** don't open the Details panels beyond the one proven click, don't run sandbox recon, don't take the quiz, don't show the audit tab — every one of those is a judge-question trap, not a pitch beat.
