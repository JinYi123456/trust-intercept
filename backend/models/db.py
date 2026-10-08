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
    QuizAttempt,
    PatternMastery,
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
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES cases(id),
    pattern_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    total INTEGER NOT NULL,
    accuracy REAL NOT NULL,
    missed_indexes TEXT NOT NULL,
    focus_areas TEXT NOT NULL,
    completed_at TEXT NOT NULL
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


# ---------------------------------------------------------------------------
# Adaptive awareness learning outcomes
# ---------------------------------------------------------------------------

def save_quiz_attempt(attempt: QuizAttempt) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO quiz_attempts (case_id, pattern_name, score, total, accuracy, missed_indexes, focus_areas, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (attempt.case_id, attempt.pattern_name, attempt.score, attempt.total, attempt.accuracy,
             json.dumps(attempt.missed_indexes), json.dumps(attempt.focus_areas), attempt.completed_at.isoformat()),
        )

def _mastery_band(accuracy: float, attempts: int) -> str:
    if accuracy >= 0.90 and attempts >= 2:
        return "mastered"
    if accuracy >= 0.80:
        return "strong"
    if accuracy >= 0.60:
        return "building"
    return "developing"

def get_pattern_mastery(pattern_name: str) -> PatternMastery:
    with _db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) attempts, COALESCE(SUM(total),0) questions_seen, COALESCE(SUM(score),0) correct_answers FROM quiz_attempts WHERE pattern_name = ?",
            (pattern_name,),
        ).fetchone()
        focus_rows = conn.execute(
            "SELECT focus_areas FROM quiz_attempts WHERE pattern_name = ? ORDER BY id DESC LIMIT 10",
            (pattern_name,),
        ).fetchall()
    attempts = int(row["attempts"] or 0)
    questions_seen = int(row["questions_seen"] or 0)
    correct = int(row["correct_answers"] or 0)
    accuracy = round(correct / questions_seen, 3) if questions_seen else 0.0
    counts: dict[str, int] = {}
    for item in focus_rows:
        for area in json.loads(item["focus_areas"] or "[]"):
            counts[area] = counts.get(area, 0) + 1
    next_focus = [name for name, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:3]]
    return PatternMastery(pattern_name=pattern_name, attempts=attempts, questions_seen=questions_seen,
                          correct_answers=correct, accuracy=accuracy,
                          mastery_band=_mastery_band(accuracy, attempts), next_focus=next_focus)

def list_quiz_attempts(case_id: str) -> list[QuizAttempt]:
    with _db() as conn:
        rows = conn.execute("SELECT * FROM quiz_attempts WHERE case_id = ? ORDER BY id", (case_id,)).fetchall()
    return [QuizAttempt(case_id=r["case_id"], pattern_name=r["pattern_name"], score=r["score"], total=r["total"], accuracy=r["accuracy"], missed_indexes=json.loads(r["missed_indexes"]), focus_areas=json.loads(r["focus_areas"]), completed_at=r["completed_at"]) for r in rows]
