"""Loads the English prompt templates from agent/prompts/*.txt.

Each template is a Python ``str.format`` skeleton. Callers pass a context dict;
``load_prompt`` renders it and raises a clear error if a placeholder is missing.
"""
from __future__ import annotations

from string import Formatter
from typing import Any

from backend.config import PROMPTS_DIR


def load_prompt(name: str, context: dict[str, Any]) -> str:
    """Render ``prompts/{name}.txt`` with ``context`` (all values English-only)."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    template = path.read_text(encoding="utf-8")
    try:
        return template.format(**context)
    except KeyError as exc:
        raise KeyError(f"Prompt '{name}' is missing context key: {exc}") from exc


def expected_fields(name: str) -> set[str]:
    """The placeholders a template expects (used by tests and sanity checks)."""
    path = PROMPTS_DIR / f"{name}.txt"
    template = path.read_text(encoding="utf-8") if path.exists() else ""
    return {field for _, field, _, _ in Formatter().parse(template) if field}
