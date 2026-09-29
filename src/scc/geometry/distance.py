"""Расстояние до цели. См. docs/01_theory/03_distance_to_goal.md."""
from __future__ import annotations

import math
from collections.abc import Mapping

from scc.models import Goal


def progress(goal: Goal) -> float:
    """Progress = Σ w_i q_i / Σ w_i."""
    total_w = sum(r.weight for r in goal.requirements)
    if total_w == 0:
        return 0.0
    return sum(r.weight * r.q for r in goal.requirements) / total_w


def completion_distance(goal: Goal) -> float:
    """D_completion = 1 − Progress."""
    return 1.0 - progress(goal)


def weighted_distance(goal: Goal) -> float:
    """D = sqrt(Σ w_i (1 − q_i)^2), веса нормированы."""
    total_w = sum(r.weight for r in goal.requirements) or 1.0
    return math.sqrt(sum((r.weight / total_w) * (1.0 - r.q) ** 2 for r in goal.requirements))


def goal_reached(goal: Goal) -> bool:
    """G(S) = 1 ⟺ все hard constraints выполнены ∧ Progress ≥ Q_min."""
    hard_ok = all(r.q >= 1.0 for r in goal.requirements if r.hard)
    return hard_ok and progress(goal) >= goal.q_min


def cost_to_go(estimate: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Оценка D_cost = α·Tokens + β·Steps + γ·$ + δ·Time + ε·Risk.

    estimate: ожидаемые остаточные {tokens, steps, money, time_s, risk}.
    weights:  config['cost_weights'].
    """
    return (
        weights["alpha_tokens"] * estimate.get("tokens", 0.0)
        + weights["beta_steps"] * estimate.get("steps", 0.0)
        + weights["gamma_money"] * estimate.get("money", 0.0)
        + weights["delta_time_s"] * estimate.get("time_s", 0.0)
        + weights["epsilon_risk"] * estimate.get("risk", 0.0)
    )
