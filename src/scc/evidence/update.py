"""Обновление оценки состояния по evidence: D̂_{t+1} = Update(D̂_t, evidence)."""
from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping

from scc.geometry.distance import completion_distance
from scc.models import Evidence, Goal


def apply_evidence(goal: Goal, evidence: Iterable[Evidence], weights: Mapping[str, float]) -> Goal:
    """Возвращает новую Goal: q_i сдвигается к наблюдению пропорционально доверию к источнику.

    Более доверенный источник (CI > commit) перезаписывает менее доверенный сильнее.
    """
    g = copy.deepcopy(goal)
    by_id = {r.id: r for r in g.requirements}
    for ev in evidence:
        req = by_id.get(ev.requirement_id)
        if req is None:
            continue
        trust = weights.get(ev.kind.value, 0.0)
        req.q = (1 - trust) * req.q + trust * ev.q_observed
        if trust >= weights.get(req.source, 0.0):
            req.source = ev.kind.value
    return g


def estimation_gap(estimated: Goal, verified: Goal) -> float:
    """GAP = D_verified − D_estimated. > 0 — агент переоценивает прогресс."""
    return completion_distance(verified) - completion_distance(estimated)
