import pytest

from scc.geometry.context import context_density, context_entropy, context_friction
from scc.geometry.distance import completion_distance, goal_reached
from scc.geometry.dynamics import alignment_angle, context_inflation, diagnose, token_efficiency
from scc.geometry.fragmentation import optimal_fragments
from scc.models import ContextBreakdown, Goal, Requirement


def example_goal():
    # пример из docs/01_theory/03_distance_to_goal.md
    rows = [("arch", .10, 1.0), ("backend", .25, .7), ("frontend", .20, .4), ("tests", .20, .5),
            ("security", .10, .2), ("docs", .05, .8), ("acceptance", .10, .6)]
    return Goal([Requirement(i, w, q) for i, w, q in rows])


def test_completion_distance_example():
    assert completion_distance(example_goal()) == pytest.approx(1 - 0.575)


def test_hard_constraint_blocks_goal():
    g = Goal([Requirement("backend", 1, 1.0), Requirement("critical_bug", 0.01, 0.0, hard=True)], q_min=0.9)
    assert not goal_reached(g)


def test_density_and_friction():
    c = ContextBreakdown(useful=8315, redundant=5112, stale=3814, conflict=1180)
    assert context_density(c) == pytest.approx(8315 / 18421)
    assert 0 < context_friction(c) <= 1
    assert 0 < context_entropy(c) <= 1


def test_token_efficiency_agent_a_beats_b():
    assert token_efficiency(-0.30, 20_000) > token_efficiency(-0.05, 80_000)


def test_inflation_high_without_progress():
    assert context_inflation(50_000, 0.0) > context_inflation(50_000, -0.2)


def test_map_correction_vs_regression():
    assert diagnose([0.51, 0.67], [0.40, 0.12]) == "map_correction"
    assert diagnose([0.51, 0.67], [0.40, 0.45]) == "regression"
    assert diagnose([1.0, 1.0]) == "stagnation"


def test_alignment_angle():
    assert alignment_angle([1, 0], [1, 0]) == pytest.approx(0)
    assert alignment_angle([0, 1], [1, 0]) == pytest.approx(90)


def test_optimal_fragmentation_u_curve():
    n_star = optimal_fragments(lambda n: 100 / n, lambda n: 4 * n, n_max=20)
    assert 1 < n_star < 20
