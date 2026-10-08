# Source & Reproducibility

## Repository
trust-intercept

## Local validation
Backend:
`PYTHONPATH=. pytest -q`

Frontend:
`cd frontend && npm install && npm run build`

## Offline baseline
Set `LLM_PROVIDER=none`. The deterministic engine remains available without hosted inference.

## Secrets
No API keys belong in source control. Use `.env.example` as the template.

## Deployment
Docker configuration is under `deployment/`. Vercel SPA fallback is configured under `frontend/vercel.json`.

## Public-source hygiene
Do not publish private operator instructions, credentials, personal test evidence, local databases, logs or generated archives.
