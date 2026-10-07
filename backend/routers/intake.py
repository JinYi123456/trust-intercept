"""Intake — accepts text / image / URL / QR submissions and creates a Case.

Framework section 02 (Inputs & Evidence): the frontend tags the input type and
sends it as a single Case object. Evidence normalisation (OCR, QR decode, PII
redaction) runs inside the orchestrator BEFORE any LLM call.
"""
from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, HTTPException, Query

from backend.agent.orchestrator import get_orchestrator
from backend.config import get_settings
from backend.models import db
from backend.models.case import Case, CaseCreate, CaseView, InputType
from backend.tools.ocr import OcrError
from backend.tools.qr_decode import QrDecodeError

router = APIRouter(tags=["intake"])


@router.post("/case", response_model=CaseView, summary="Submit a suspicious artefact for investigation")
def submit_case(payload: CaseCreate) -> CaseView:
    settings = get_settings()

    if payload.input_type == InputType.TEXT and not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text input is empty.")
    if payload.input_type == InputType.URL and not payload.url.strip():
        raise HTTPException(status_code=400, detail="URL input is empty.")
    if payload.input_type in (InputType.IMAGE, InputType.QR_IMAGE) and not payload.image_b64:
        raise HTTPException(status_code=400, detail="This case type requires an uploaded image.")
    if payload.input_type == InputType.AUDIO and not payload.audio_b64:
        raise HTTPException(status_code=400, detail="Audio cases require an uploaded audio file (mp3/wav/m4a).")

    image_bytes: bytes | None = None
    if payload.image_b64:
        try:
            image_bytes = base64.b64decode(payload.image_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"image_b64 is not valid base64: {exc}") from exc
        if len(image_bytes) > settings.max_image_bytes:
            raise HTTPException(status_code=413, detail="Image exceeds the 10 MB limit.")

    audio_bytes: bytes | None = None
    if payload.audio_b64:
        try:
            audio_bytes = base64.b64decode(payload.audio_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"audio_b64 is not valid base64: {exc}") from exc
        if len(audio_bytes) > settings.max_audio_bytes:
            raise HTTPException(status_code=413, detail="Audio exceeds the 20 MB limit.")

    case = Case(
        input_type=payload.input_type,
        raw_text=payload.text or "",
        url=payload.url.strip(),
        image_filename=payload.image_filename,
        audio_filename=payload.audio_filename,
        request_modules=payload.request_modules,
    )

    orchestrator = get_orchestrator()
    try:
        orchestrator.process_case(case, image_bytes=image_bytes, audio_bytes=audio_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OcrError as exc:
        raise HTTPException(status_code=422, detail=f"OCR failed: {exc}") from exc
    except QrDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"QR decoding failed: {exc}") from exc

    view = orchestrator.build_case_view(case.id)
    if view is None:  # pragma: no cover — the case was just created
        raise HTTPException(status_code=500, detail="Case was created but could not be loaded.")
    return view


@router.get("/case/{case_id}", response_model=CaseView, summary="Load a case with verdict, evidence and decisions")
def get_case(case_id: str) -> CaseView:
    view = get_orchestrator().build_case_view(case_id)
    if view is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return view


@router.get("/cases", summary="Demo metrics — every case with its latest verdict score")
def list_cases(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    """Evidence-of-value metrics for the demo: cases processed, scores, decisions."""
    orchestrator = get_orchestrator()
    results: list[dict] = []
    for row in db.list_case_rows(limit=limit):
        verdict = db.latest_verdict(row["id"])
        results.append(
            {
                "id": row["id"],
                "input_type": row["input_type"],
                "status": row["status"],
                "created_at": row["created_at"],
                "score": verdict.score.value if verdict else None,
                "confidence": verdict.confidence.value if verdict else None,
                "decision_count": db.count_decisions(row["id"]),
            }
        )
    return results
