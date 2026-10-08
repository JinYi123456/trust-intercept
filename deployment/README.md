# TRUST//INTERCEPT deployment runbook

## Recommended competition deployment

Use a **split deployment**:

```text
Vercel
  ↓
TRUST//INTERCEPT React frontend
  ↓ HTTPS
FastAPI backend (Render / Railway / Fly.io / VM / equivalent)
  ↓
LLM provider + optional reputation tools + persistent storage
```

Vercel hosts the static Vite/React frontend. The backend is a separate FastAPI service because provider API keys must remain server-side and the current backend is not configured as a Vercel Python serverless function.

### Vercel frontend environment

Set this build-time variable in the Vercel project:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND-DOMAIN.example.com
```

This is a public URL, not a secret.

Do **not** put any of these into Vercel frontend environment variables:

```text
GONKA_API_KEY
FEATHERLESS_API_KEY
GEMINI_API_KEY
VIRUSTOTAL_API_KEY
SAFE_BROWSING_API_KEY
GOOGLE_VISION_API_KEY
```

### FastAPI backend environment

For the live competition demo, the recommended provider is Gonka:

```text
LLM_PROVIDER=gonka
GONKA_API_KEY=<secret stored in backend host secret manager>
GONKA_MODEL=MiniMaxAI/MiniMax-M2.7
ALLOW_OUTBOUND_LOOKUPS=true
CORS_ORIGINS=https://YOUR-VERCEL-DOMAIN.vercel.app
```

Optional fallback providers may be configured with their own server-side keys:

```text
FEATHERLESS_API_KEY=
GEMINI_API_KEY=
```

The backend never returns the key values through `/health` or `/ready`; only configured/not-configured status is exposed.

## Live demo profile

The intended judge/demo path uses real hosted inference, not the offline engine:

```text
LLM_PROVIDER=gonka
ALLOW_OUTBOUND_LOOKUPS=true
OCR_CLOUD_FALLBACK=false
```

If the demo provider becomes unavailable, the deterministic local engine remains available as a recovery path.

## Offline recovery profile

For a no-network fallback:

```text
LLM_PROVIDER=none
ALLOW_OUTBOUND_LOOKUPS=false
OCR_CLOUD_FALLBACK=false
```

This is a backup mode, not the primary competition demo configuration.

## Backend

Run locally:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Health endpoints:

- `/health` — liveness/configuration summary
- `/ready` — deployment readiness and database status

## Storage

SQLite is suitable for the hackathon demo when attached to persistent storage. For a production service, use a persistent volume or migrate to a managed database before treating the deployment as production infrastructure.

## Security

- Never commit `.env` or provider keys.
- Use HTTPS for frontend and backend.
- Restrict `CORS_ORIGINS` to the actual Vercel domain.
- Keep provider secrets only on the backend host.
- Do not expose `/docs` publicly unless needed.
- Keep outbound URL access controlled by `ALLOW_OUTBOUND_LOOKUPS` and the tool URL policy.
