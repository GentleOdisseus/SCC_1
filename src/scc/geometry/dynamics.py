"""Динамика траектории. См. docs/01_theory/04_dynamics.md."""
from __future__ import annotations

import math
from collections.abc import Sequence

EPS = 1e-6


def goal_velocity(d_series: Sequence[float]) -> float:
    """v_G = −ΔD/Δt на последнем шаге (Δt = 1 шаг)."""
    return -(d_series[-1] - d_series[-2]) if len(d_series) >= 2 else 0.0


def goal_acceleration(d_series: Sequence[float]) -> float:
    """a_G = Δv_G/Δt."""
    if len(d_series) < 3:
        return 0.0
    return goal_velocity(d_series) - goal_velocity(d_series[:-1])


def token_efficiency(delta_d: float, delta_tokens: int) -> float:
    """η = −ΔD / ΔTokens (на 1000 токенов)."""
    return -delta_d / (delta_tokens / 1000) if delta_tokens else 0.0


def context_inflation(delta_c: int, delta_d: float, eps: float = 1e-3) -> float:
    """I = ΔC / (−ΔD + ε), ΔC в тысячах токенов. Большое I — «думает вокруг задачи»."""
    progress = max(-delta_d, 0.0)
    return (delta_c / 1000) / (progress + eps)


def alignment_angle(action: Sequence[float], to_goal: Sequence[float]) -> float:
    """θ — угол (в градусах) между вектором действия и направлением к цели."""
    dot = sum(a * b for a, b in zip(action, to_goal))
    na = math.sqrt(sum(a * a for a in action))
    nb = math.sqrt(sum(b * b for b in to_goal))
    if na < EPS or nb < EPS:
        return 90.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (na * nb)))))


def diagnose(d_series: Sequence[float], u_series: Sequence[float] | None = None,
             stall: float = 0.005) -> str:
    """accelerating | decelerating | stagnation | regression | map_correction."""
    v = goal_velocity(d_series)
    if abs(v) < stall:
        return "stagnation"
    if v < 0:
        if u_series and len(u_series) >= 2 and u_series[-1] < u_series[-2]:
            return "map_correction"
        return "regression"
    return "accelerating" if goal_acceleration(d_series) >= 0 else "decelerating"
