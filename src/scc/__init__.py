"""SCC — Agentic State Geometry / Geometric Context Controller."""
from scc.config import load_config
from scc.models import ContextBreakdown, ContextNode, Distance, Evidence, EvidenceKind, Goal, Requirement

__all__ = [
    "load_config", "ContextBreakdown", "ContextNode", "Distance",
    "Evidence", "EvidenceKind", "Goal", "Requirement",
]
__version__ = "0.0.1"
