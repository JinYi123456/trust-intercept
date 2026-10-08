# TRUST//INTERCEPT deployment runbook

TRUST//INTERCEPT is designed to run with a separate frontend and FastAPI backend.
The product remains usable with `LLM_PROVIDER=none` and `ALLOW_OUTBOUND_LOOKUPS=false`.

## Backend

Recommended production environment variables:

- `CORS_ORIGINS=https://<your-frontend-domain>`
- `LLM_PROVIDER=auto` (or `none` for fully offline mode)
- provider API keys only through the host's secret manager
- `ALLOW_OUTBOUND_LOOKUPS=false` unless live URL inspection is explicitly required
- `DB_PATH=/data/trust-intercept.db` on a persistent volume

Health endpoints:

- `/health` — liveness/configuration summary
- `/ready` — deployment readiness, database status and offline fallback status

## Frontend

Set `VITE_API_BASE_URL` to the deployed backend origin before building.
The frontend is a static Vite application and can be deployed to Vercel, Netlify,
or any static host that supports SPA fallback to `index.html`.

## Demo/offline mode

For a deterministic local demonstration:

```text
LLM_PROVIDER=none
ALLOW_OUTBOUND_LOOKUPS=false
OCR_CLOUD_FALLBACK=false
```

The core decision-defence pipeline continues to run locally. This mode avoids
provider quota, external-network dependency and accidental contact with live URLs.

## Production safety

- Never commit `.env` or API keys.
- Use HTTPS for the frontend and backend.
- Keep the SQLite file on persistent storage if using the local persistence mode.
- Disable outbound lookups unless the deployment explicitly needs them.
- Do not expose `/docs` publicly unless API exploration is required.
