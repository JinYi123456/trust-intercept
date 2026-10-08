# TRUST//INTERCEPT — Final Submission Release Notes

Release candidate: Phase 16

TRUST//INTERCEPT is an agentic decision-defence system for scam awareness and intervention.

Core flow: INTAKE → NORMALISE → ROUTE → HUNT → SKEPTIC → VERIFY → ARBITRATE → INTERCEPT → HUMAN APPROVAL → VERIFY / PAUSE / REPORT → LEARN

Validated characteristics:
- 47 backend tests passing, including an 8-test end-to-end demo smoke suite (`backend/tests/test_e2e_smoke.py`) covering the three judge flows: scam → HIGH verdict → human approval; legitimate → LOW with zero false alarm; and `LLM_PROVIDER=none` offline fallback completing the same flows.
- Evaluation Lab benchmark v2: 77 cases (20 verbatim from the SMS Spam Collection, 57 synthetic), across English/Malay/Manglish and SMS/email/URL/QR channels — see `docs/EVALUATION_SUMMARY.md`.
- Deterministic-engine benchmark results (our benchmark, not a product claim): accuracy 0.675, precision 0.818, recall 0.730, F1 0.771, false-positive rate 0.214 — with all 16 failure cases published in the evaluation summary and served live by `GET /evaluation`.
- Malaysia-specific grounding: Macau scam, parcel-fee (PosLaju/J&T), e-wallet freeze (TNG/Boost/ShopeePay) and LHDN/PDRM impersonation patterns; report destinations (NSRC 997, Semak Mule, BNM, CCID) embedded in every report bundle.
- Startup banner prints which LLM provider is live vs deterministic fallback.
- Prompt-injection and unsafe network-target controls are tested.
- Offline deterministic mode is available without hosted LLM inference (0 hosted calls per case; hosted mode capped at 2).
- Case Replay is read-only and does not re-open suspicious destinations.
- Private operator instructions are excluded from the public release candidate.

Metric qualification: benchmark figures describe the maintained local benchmark (deterministic mode) only and are not real-world detection guarantees. The one-in-five false-positive rate at this stage is a documented argument for the human-approval design: nothing is sent, blocked, or filed without an explicit human decision.


## Intended deployment
The competition release uses a Vercel-hosted frontend and a separately hosted FastAPI backend. The live demo uses a real hosted LLM API key stored only on the backend host. Offline mode is retained as a recovery path.

Vercel frontend configuration:
- Root Directory: `frontend/`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment: `VITE_API_BASE_URL=https://YOUR-BACKEND-DOMAIN.example.com`

Backend demo configuration:
- `LLM_PROVIDER=gonka`
- `GONKA_API_KEY=<secret>`
- `ALLOW_OUTBOUND_LOOKUPS=true` when live URL inspection is required
- `CORS_ORIGINS=https://YOUR-VERCEL-DOMAIN.vercel.app`
