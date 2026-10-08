# TRUST//INTERCEPT — Final Submission Checklist

## Product
- [ ] `PYTHONPATH=. pytest -q`
- [ ] `cd frontend && npm install && npm run build`
- [ ] Confirm `/health` and `/ready`
- [ ] Configure the live demo backend with `LLM_PROVIDER=gonka` and the real provider key stored only in backend secrets
- [ ] Set `ALLOW_OUTBOUND_LOOKUPS=true` if the demo case requires live URL/reputation inspection
- [ ] Test the offline recovery path with `LLM_PROVIDER=none`
- [ ] Confirm suspicious links are not opened automatically
- [ ] Confirm human approval gate before consequential actions

## Security
- [ ] No `.env` or API keys committed
- [ ] `PRIVATE_OPERATOR_MANUAL.md` ignored and not public
- [ ] Run repository secret scan
- [ ] Keep private/local test evidence out of public repo

## Demo
- [ ] Parcel-delivery scam case
- [ ] Legitimate case for false-positive handling
- [ ] Offline fallback case
- [ ] Browser + terminal ready
- [ ] Use `submission/03_demo/DEMO_SCRIPT.md`

## Submission
- [ ] Replace team placeholders
- [ ] Export proposal PDF
- [ ] Export pitch deck PPTX/PDF
- [ ] Add final screenshots/evidence
- [ ] Set Vercel project root to `frontend/` and `VITE_API_BASE_URL` to the deployed FastAPI backend
- [ ] Verify backend CORS allows the exact Vercel domain
- [ ] Verify public GitHub repository
