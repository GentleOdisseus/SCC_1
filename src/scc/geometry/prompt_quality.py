"""Transparent heuristic for prompt specification completeness."""
from __future__ import annotations

import re
from typing import Any

_PROMPT_CUES: dict[str, tuple[str, ...]] = {
    "goal": (
        r"\b(?:создай|сделай|разработай|добавь|исправь|напиши|реализуй|построй|запусти|обнови)\b",
        r"\b(?:create|make|develop|add|fix|write|implement|build|run|update)\b",
    ),
    "constraints": (
        r"\b(?:без|только|не|должен|должна|должно|используй|огранич|запрещ)\w*\b",
        r"\b(?:without|only|must|should|don't|do not|use|avoid|constraint|limit)\b",
    ),
    "deliverable": (
        r"\b(?:игр\w*|змейк\w*|приложен\w*|скрипт\w*|файл\w*|компонент\w*|отч[её]т\w*|результат\w*|формат\w*)\b",
        r"\b(?:game|application|app|script|file|component|report|deliverable|output|format)\b",
    ),
    "acceptance_checks": (
        r"\b(?:тест\w*|провер\w*|критери\w*|при[её]мк\w*|верификатор\w*)\b",
        r"\b(?:test\w*|check\w*|acceptance|criteria|verifier\w*|passes|validation)\b",
    ),
}


def assess_prompt(text: str) -> dict[str, Any]:
    """Return visible checklist flags and an equal-weight completeness estimate.

    This detects cue words only; it does not judge correctness, feasibility, or
    whether the described requirements are mutually consistent.
    """
    normalized = text.casefold()
    criteria = {
        name: any(re.search(pattern, normalized) for pattern in patterns)
        for name, patterns in _PROMPT_CUES.items()
    }
    score = sum(criteria.values()) / len(criteria)
    return {
        "score": score,
        "criteria": criteria,
        "method": "keyword_checklist_heuristic",
        "limitations": "Measures cue presence, not semantic quality or correctness.",
    }
