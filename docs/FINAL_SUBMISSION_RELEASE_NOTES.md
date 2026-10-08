# TRUST//INTERCEPT — Final Submission Release Notes

Release candidate: Phase 16

TRUST//INTERCEPT is an agentic decision-defence system for scam awareness and intervention.

Core flow: INTAKE → NORMALISE → ROUTE → HUNT → SKEPTIC → VERIFY → ARBITRATE → INTERCEPT → HUMAN APPROVAL → VERIFY / PAUSE / REPORT → LEARN

Validated characteristics:
- 39 backend regression tests passing at the Phase 16 audit.
- Maintained benchmark includes scam, legitimate, borderline and adversarial cases.
- Prompt-injection and unsafe network-target controls are tested.
- Offline deterministic mode is available without hosted LLM inference.
- Case Replay is read-only and does not re-open suspicious destinations.
- Private operator instructions are excluded from the public release candidate.

Metric qualification: the maintained benchmark currently reports 100% accuracy, precision, recall and F1 with 0% false-positive rate. These figures describe the maintained local benchmark only and are not real-world detection guarantees.


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
