"""Report — download the redacted Module 3 report bundle.

Framework section 04 (Defensive Actions): TRUST//INTERCEPT prepares the report; the human
sends it. The bundle only exists after the user approved the `report` action on
the Review screen.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.models import db
from backend.models.case import ReportBundle

router = APIRouter(tags=["report"])


@router.get(
    "/case/{case_id}/report",
    summary="Fetch the redacted report bundle (JSON or markdown download)",
    response_model=None,
)
def get_report(
    case_id: str,
    format: str = Query(default="json", pattern="^(json|markdown)$"),
) -> Response | ReportBundle:
    payload = db.get_artifact(case_id, "report")
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No report bundle exists for case {case_id}. "
                "Approve the 'report' action on the review screen first."
            ),
        )

    bundle = ReportBundle(**payload)
    if format == "markdown":
        return Response(
            content=bundle.report_markdown,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="trust-intercept-report-{case_id}.md"'
            },
        )
    return bundle
