"""Context mass и центр тяжести проекта. См. docs/01_theory/02_context_metrics.md."""
from __future__ import annotations

import math
from collections.abc import Sequence

from scc.models import ContextNode


def node_mass(node: ContextNode, w_tok: float = 1.0, w_dep: float = 0.1, w_unc: float = 0.5) -> float:
    """m_i = f(tokens, dependencies, uncertainty) — линейная стартовая форма."""
    return (w_tok * node.context.total / 1000
            + w_dep * len(node.dependencies)
            + w_unc * node.uncertainty)


def center_of_mass(nodes: Sequence[ContextNode]) -> tuple[float, ...]:
    """X_center = Σ m_i X_i / Σ m_i."""
    masses = [node_mass(n) for n in nodes]
    total = sum(masses)
    if not nodes or total == 0:
        return ()
    dim = len(nodes[0].position)
    return tuple(sum(m * n.position[k] for m, n in zip(masses, nodes)) / total for k in range(dim))


def center_goal_distance(nodes: Sequence[ContextNode], goal_pos: Sequence[float]) -> float:
    """D_center→goal = ‖X_center − G‖."""
    c = center_of_mass(nodes)
    return math.dist(c, goal_pos) if c else float("inf")
