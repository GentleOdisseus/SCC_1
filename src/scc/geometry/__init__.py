"""Geometry Engine. См. docs/02_architecture/geometry_engine.md."""
from scc.geometry.context import context_density, context_entropy, context_friction
from scc.geometry.distance import completion_distance, cost_to_go, goal_reached, weighted_distance
from scc.geometry.dynamics import (
    alignment_angle, context_inflation, diagnose, goal_acceleration, goal_velocity, token_efficiency,
)
from scc.geometry.mass import center_of_mass, node_mass

__all__ = [
    "context_density", "context_entropy", "context_friction",
    "completion_distance", "cost_to_go", "goal_reached", "weighted_distance",
    "alignment_angle", "context_inflation", "diagnose", "goal_acceleration", "goal_velocity",
    "token_efficiency", "center_of_mass", "node_mass",
]
