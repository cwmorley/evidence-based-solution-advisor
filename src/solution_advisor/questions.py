"""Identify useful next questions from absent intake fields."""

from __future__ import annotations

from typing import Any

from .io import get_path


MISSING = object()


def next_questions(
    intake: dict[str, Any], catalog: list[dict[str, Any]], limit: int = 5
) -> list[dict[str, str]]:
    missing = []
    for entry in sorted(catalog, key=lambda item: item.get("priority", 100)):
        value = get_path(intake, entry["path"], MISSING)
        if value is MISSING or value is None or value == "" or value == []:
            missing.append(
                {
                    "field": entry["path"],
                    "question": entry["question"],
                    "why_it_matters": entry["why_it_matters"],
                }
            )
    return missing[:limit]
