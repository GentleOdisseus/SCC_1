"""Пороговая политика v0. Приоритеты — docs/02_architecture/controller.md."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from scc.controller.actions import Action


@dataclass
class GeometrySnapshot:
    goal_reached: bool
    d_completion: float
    u_d: float
    goal_velocity: float
    uncertainty_dropped: bool = False
    context_density: float = 1.0
    context_entropy: float = 0.0
    context_inflation: float = 0.0
    estimation_gap: float = 0.0
    merge_risk: float = 1.0
    merge_candidate: bool = False
    fragments: int = 1
    oversized_node: bool = False


@dataclass
class Decision:
    actions: list[Action]
    reasons: list[str] = field(default_factory=list)


class ThresholdPolicy:
    def __init__(self, thresholds: Mapping[str, float]):
        self.t = thresholds

    def decide(self, s: GeometrySnapshot) -> Decision:
        t = self.t
        if s.goal_reached:
            return Decision([Action.STOP], ["goal region reached"])
        if s.goal_velocity < -t["goal_velocity_stall"] and not s.uncertainty_dropped:
            return Decision([Action.ROLLBACK], ["regression without map correction"])
        if s.estimation_gap > t["estimation_gap_max"]:
            return Decision([Action.VERIFY], [f"estimation gap {s.estimation_gap:.2f}"])
        if s.u_d > t["uncertainty_verify"]:
            return Decision([Action.RETRIEVE, Action.VERIFY], [f"uncertainty {s.u_d:.2f}"])
        if s.context_inflation > t["context_inflation_max"]:
            return Decision([Action.COMPRESS, Action.REPLAN], [f"inflation {s.context_inflation:.1f}"])
        if s.context_density < t["context_density_min"]:
            return Decision([Action.COMPRESS, Action.ARCHIVE], [f"density {s.context_density:.2f}"])
        if s.context_entropy > t["context_entropy_max"]:
            return Decision([Action.COMPRESS], [f"entropy {s.context_entropy:.2f}"])
        if s.merge_candidate and s.merge_risk < t["merge_risk_max"]:
            return Decision([Action.MERGE], ["close branches, low merge risk"])
        if (s.oversized_node and abs(s.goal_velocity) < t["goal_velocity_stall"]
                and s.fragments < t["max_fragments"]):
            return Decision([Action.SPLIT], ["massive node without progress"])
        return Decision([Action.CONTINUE])
