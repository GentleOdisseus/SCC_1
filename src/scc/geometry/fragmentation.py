"""Optimal Fragmentation (закон III). См. docs/01_theory/04_dynamics.md."""
from __future__ import annotations

from collections.abc import Callable


def total_cost(n: int, reasoning: Callable[[int], float], coordination: Callable[[int], float]) -> float:
    """Cost(n) = ReasoningCost(n) + CoordinationCost(n)."""
    return reasoning(n) + coordination(n)


def optimal_fragments(reasoning: Callable[[int], float], coordination: Callable[[int], float],
                      n_max: int = 20) -> int:
    """n* = argmin Cost(n) на 1..n_max. Модели стоимости — калибруются в эксперименте E3."""
    return min(range(1, n_max + 1), key=lambda n: total_cost(n, reasoning, coordination))
