"""Доменные модели Agentic State Geometry. См. docs/01_theory/01_state_space.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Requirement:
    """Проверяемая координата цели g_i с весом w_i и выполнением q_i ∈ [0, 1]."""
    id: str
    weight: float
    q: float = 0.0
    hard: bool = False          # hard constraint: цель недостижима, пока q < 1
    source: str = "llm_self_report"  # откуда получено q (тип evidence)


@dataclass
class Goal:
    """Цель как область G: hard constraints + порог качества Q_min."""
    requirements: list[Requirement]
    q_min: float = 1.0


@dataclass
class ContextBreakdown:
    """C_i = useful + redundant + stale + conflict (в токенах)."""
    useful: int = 0
    redundant: int = 0
    stale: int = 0
    conflict: int = 0

    @property
    def total(self) -> int:
        return self.useful + self.redundant + self.stale + self.conflict


@dataclass
class ContextNode:
    """Узел контекста / подзадача: (r, d, ρ, u, c) + связи графа."""
    id: str
    context: ContextBreakdown = field(default_factory=ContextBreakdown)
    goal_distance: float = 1.0
    uncertainty: float = 0.0
    tokens_spent: int = 0
    dependencies: list[str] = field(default_factory=list)
    parent: str | None = None
    position: tuple[float, ...] = (0.0, 0.0)   # координаты в проекции state space


@dataclass(frozen=True)
class Distance:
    """D(S, G) = (D_completion, D_cost, U_D). См. ADR-0001."""
    completion: float
    cost: float
    uncertainty: float

    @property
    def interval(self) -> tuple[float, float]:
        return (max(0.0, self.completion - self.uncertainty), min(1.0, self.completion + self.uncertainty))


class EvidenceKind(str, Enum):
    LLM_SELF_REPORT = "llm_self_report"
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    CI = "ci"
    INTEGRATION_TEST = "integration_test"
    USER_ACCEPTANCE = "user_acceptance"
    PRODUCTION_VERIFICATION = "production_verification"


@dataclass
class Evidence:
    """Наблюдение, меняющее оценку q_i требования. Commit ≠ progress (ADR-0002)."""
    kind: EvidenceKind
    requirement_id: str
    q_observed: float
    ref: str = ""          # sha, PR number, CI run id
    cost_tokens: int = 0
