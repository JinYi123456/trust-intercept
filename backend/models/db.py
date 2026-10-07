"""SQLite persistence for the TRUST//INTERCEPT demo.

Stores REDACTED case data only — the unredacted original text and the PII map
(with original values) never reach this database (see tools/pii_redact.py and
agent/orchestrator.py). Verdicts are append-only so a "disagree" decision can
preserve the original verdict alongside the re-checked one.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from backend.config import get_settings
from backend.models.case import (
    Case,
    CaseStatus,
    Decision,
    Evidence,
    InputType,
    Quiz,
    ReportBundle,
    Verdict,
    utcnow,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id            TEXT PRIMARY KEY,
    input_type    TEXT NOT NULL,
    redacted_text TEXT NOT NULL DEFAULT '',
    url           TEXT NOT NULL DEFAULT '',
    image_filename TEXT NOT NULL DEFAULT '',
    audio_filename TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id      TEXT NOT NULL REFERENCES cases(id),
    tool         TEXT NOT NULL,
    raw_output   TEXT NOT NULL,
    collected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verdicts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    TEXT NOT NULL REFERENCES cases(id),
    payload    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id         TEXT PRIMARY KEY,
    case_id    TEXT NOT NULL REFERENCES cases(id),
    payload    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
    case_id    TEXT NOT NULL REFERENCES cases(id),
    kind       TEXT NOT NULL,
    payload    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (case_id, kind)
);
CREATE TABLE IF NOT EXISTS community_hashes (
    hash         TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    risk         TEXT NOT NULL,
    source       TEXT NOT NULL,
    report_count INTEGER NOT NULL DEFAULT 1,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL
);
"""


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(get_settings().db_path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _db() as conn:
        conn.executescript(_SCHEMA)
        # Migration: databases created before audio support lack the column.
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN audio_filename TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists


# ---------------------------------------------------------------------------
# Cases (redacted snapshot only)
# ---------------------------------------------------------------------------


def create_case(case: Case) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cases (id, input_type, redacted_text, url, image_filename,"
            " audio_filename, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                case.id,
                case.input_type.value,
                "",  # redacted_text is filled in by update_case_text after redaction
                case.url,
                case.image_filename,
                case.audio_filename,
                case.status.value,
                case.created_at.isoformat(),
            ),
        )


def update_case_text(case_id: str, redacted_text: str) -> None:
    with _db() as conn:
        conn.execute("UPDATE cases SET redacted_text = ? WHERE id = ?", (redacted_text, case_id))


def update_case_status(case_id: str, status: CaseStatus) -> None:
    with _db() as conn:
        conn.execute("UPDATE cases SET status = ? WHERE id = ?", (status.value, case_id))


def get_case_row(case_id: str) -> Optional[dict[str, Any]]:
    with _db() as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return dict(row) if row else None


def list_case_rows(limit: int = 50) -> list[dict[str, Any]]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM cases ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def add_evidence(case_id: str, evidence: Evidence) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO evidence (case_id, tool, raw_output, collected_at) VALUES (?, ?, ?, ?)",
            (
                case_id,
                evidence.tool,
                json.dumps(evidence.raw_output, ensure_ascii=False, default=str),
                evidence.collected_at.isoformat(),
            ),
        )


def list_evidence(case_id: str) -> list[Evidence]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT tool, raw_output, collected_at FROM evidence WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
    return [
        Evidence(
            tool=row["tool"],
            raw_output=json.loads(row["raw_output"]),
            collected_at=row["collected_at"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Verdicts (append-only history)
# ---------------------------------------------------------------------------


def save_verdict(verdict: Verdict) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO verdicts (case_id, payload, created_at) VALUES (?, ?, ?)",
            (
                verdict.case_id,
                verdict.model_dump_json(),
                verdict.created_at.isoformat(),
            ),
        )


def list_verdicts(case_id: str) -> list[Verdict]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT payload FROM verdicts WHERE case_id = ? ORDER BY id", (case_id,)
        ).fetchall()
    return [Verdict(**json.loads(row["payload"])) for row in rows]


def latest_verdict(case_id: str) -> Optional[Verdict]:
    verdicts = list_verdicts(case_id)
    return verdicts[-1] if verdicts else None


# ---------------------------------------------------------------------------
# Decisions (the audit trail of human approvals)
# ---------------------------------------------------------------------------


def add_decision(decision: Decision) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO decisions (id, case_id, payload, created_at) VALUES (?, ?, ?, ?)",
            (
                decision.id,
                decision.case_id,
                decision.model_dump_json(),
                decision.decided_at.isoformat(),
            ),
        )


def list_decisions(case_id: str) -> list[Decision]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT payload FROM decisions WHERE case_id = ? ORDER BY created_at, rowid",
            (case_id,),
        ).fetchall()
    return [Decision(**json.loads(row["payload"])) for row in rows]


# ---------------------------------------------------------------------------
# Artifacts (report bundle / quiz)
# ---------------------------------------------------------------------------


def save_artifact(case_id: str, kind: str, payload: dict[str, Any]) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO artifacts (case_id, kind, payload, created_at)"
            " VALUES (?, ?, ?, ?)",
            (case_id, kind, json.dumps(payload, ensure_ascii=False, default=str), utcnow().isoformat()),
        )


def get_artifact(case_id: str, kind: str) -> Optional[dict[str, Any]]:
    with _db() as conn:
        row = conn.execute(
            "SELECT payload FROM artifacts WHERE case_id = ? AND kind = ?", (case_id, kind)
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def get_quiz_artifact(case_id: str) -> Optional[Quiz]:
    payload = get_artifact(case_id, "quiz")
    return Quiz(**payload) if payload else None


def get_report_artifact(case_id: str) -> Optional[ReportBundle]:
    payload = get_artifact(case_id, "report")
    return ReportBundle(**payload) if payload else None


def count_decisions(case_id: str) -> int:
    with _db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM decisions WHERE case_id = ?", (case_id,)
        ).fetchone()
    return int(row["n"]) if row else 0


def input_type_from_row(row: dict[str, Any]) -> InputType:
    return InputType(row["input_type"])
