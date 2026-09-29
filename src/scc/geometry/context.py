"""Метрики контекста. См. docs/01_theory/02_context_metrics.md."""
from __future__ import annotations

import math

from scc.models import ContextBreakdown


def context_radius(c: ContextBreakdown, scale: float = 100_000) -> float:
    """r = f(|C|): логарифмическая шкала, нормированная к [0, 1] на `scale` токенах."""
    return min(1.0, math.log1p(c.total) / math.log1p(scale))


def context_density(c: ContextBreakdown) -> float:
    """ρ = C_useful / C."""
    return c.useful / c.total if c.total else 1.0


def context_entropy(c: ContextBreakdown) -> float:
    """Нормированная энтропия Шеннона распределения по 4 категориям контекста (0..1).

    Proxy для H(C); целевая реализация — по числу альтернатив/устаревших/конфликтующих фактов.
    """
    parts = [c.useful, c.redundant, c.stale, c.conflict]
    total = sum(parts)
    if not total:
        return 0.0
    h = -sum((p / total) * math.log(p / total) for p in parts if p)
    return h / math.log(len(parts))


def context_friction(c: ContextBreakdown, noise: float = 0.0, w_conflict: float = 2.0) -> float:
    """F = f(N, R, H, X): доля «шума» с повышенным весом противоречий, clip в [0, 1]."""
    if not c.total:
        return 0.0
    polluted = c.redundant + c.stale + w_conflict * c.conflict
    return min(1.0, polluted / c.total + noise)
