"""FastAPI entrypoint for the TRUST//INTERCEPT backend.

Run from the project root:

    uvicorn backend.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.agent.llm import llm_status
from backend.config import cors_origin_list, get_settings
from backend.models import db
from backend.routers import intake, metrics, report, review

DESCRIPTION = """
Agentic scam-defence and decision-safety platform (HackAI Track 03: Scam Defence & Awareness).

**TRUST//INTERCEPT investigates, challenges, and explains; the person decides.** Every module produces
cues, a confidence band, and a *proposed* next step — nothing is blocked,
sent, or filed without an explicit human decision on `/case/{id}/decision`.
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origin_list() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(review.router)
app.include_router(report.router)
app.include_router(metrics.router)


@app.get("/evaluation", tags=["evaluation"], summary="Run the local scam-defence benchmark without persisting benchmark cases")
def evaluation() -> dict:
    from backend.agent.evaluation import run_evaluation
    return run_evaluation()


@app.get("/case/{case_id}/replay", tags=["audit"], summary="Replay the persisted redacted investigation without re-running tools")
def replay_case(case_id: str) -> dict:
    from fastapi import HTTPException
    from backend.agent.provenance import build_case_provenance
    try:
        return build_case_provenance(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health", tags=["system"], summary="Liveness + configuration status")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm": llm_status(),
        "outbound_lookups_enabled": settings.allow_outbound_lookups,
        "redirect_max_hops": settings.redirect_max_hops,
        "ocr_cloud_fallback": settings.ocr_cloud_fallback,
    }


@app.get("/ready", tags=["system"], summary="Readiness check for deployment and demo startup")
def ready() -> dict:
    """Return a deployment-safe readiness signal without exposing secrets."""
    try:
        db.init_db()
        database = "ready"
    except Exception as exc:  # pragma: no cover - deployment failure path
        database = f"error: {type(exc).__name__}"
    llm = llm_status()
    return {
        "status": "ready" if database == "ready" else "degraded",
        "database": database,
        "llm": llm,
        "offline_fallback": True,
        "outbound_lookups_enabled": settings.allow_outbound_lookups,
        "version": "1.0.0",
    }
