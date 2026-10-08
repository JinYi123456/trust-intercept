# Source & Reproducibility

## Repository
`trust-intercept`

## Local validation
Backend:
`PYTHONPATH=. pytest -q`

Frontend:
`cd frontend && npm install && npm run build`

## Live competition configuration
The primary demo uses a hosted LLM provider on the **FastAPI backend**, not in the browser. Recommended:

```text
LLM_PROVIDER=gonka
GONKA_API_KEY=<backend secret>
ALLOW_OUTBOUND_LOOKUPS=true
```

For Vercel, set only the public backend URL in the frontend build environment:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND-DOMAIN.example.com
```

Never put provider API keys in Vercel frontend variables.

## Offline recovery
Set `LLM_PROVIDER=none` and `ALLOW_OUTBOUND_LOOKUPS=false`. This is a recovery path for network/provider failure, not the primary competition demo.

## Secrets
No API keys belong in source control. Use `.env.example` as the backend template and `frontend/.env.example` for the public frontend API URL.

## Deployment
- Vercel project root: `frontend/`
- Build command: `npm run build`
- Output directory: `dist`
- Frontend variable: `VITE_API_BASE_URL`
- Backend: deploy FastAPI separately and configure its secret environment variables.

## Public-source hygiene
Do not publish private operator instructions, credentials, personal test evidence, local databases, logs or generated archives.
