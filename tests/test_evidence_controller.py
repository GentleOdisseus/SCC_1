from scc.config import load_config
from scc.controller import Action, GeometrySnapshot, ThresholdPolicy
from scc.evidence import apply_evidence, estimation_gap
from scc.models import Evidence, EvidenceKind, Goal, Requirement

CFG = load_config()


def test_ci_evidence_corrects_self_report():
    estimated = Goal([Requirement("tests", 1.0, q=0.9)])          # агент считает 90%
    ci = Evidence(EvidenceKind.CI, "tests", q_observed=0.4)        # CI: 40% тестов проходит
    verified = apply_evidence(estimated, [ci], CFG["evidence_weights"])
    assert verified.requirements[0].q < 0.9
    assert estimation_gap(estimated, verified) > 0


def test_policy_stop_and_inflation():
    p = ThresholdPolicy(CFG["controller"])
    assert p.decide(GeometrySnapshot(True, 0.0, 0.0, 0.0)).actions == [Action.STOP]
    s = GeometrySnapshot(False, 0.4, 0.1, 0.001, context_inflation=50)
    assert Action.COMPRESS in p.decide(s).actions


def test_policy_map_correction_not_rollback():
    p = ThresholdPolicy(CFG["controller"])
    s = GeometrySnapshot(False, 0.67, 0.12, -0.16, uncertainty_dropped=True)
    assert Action.ROLLBACK not in p.decide(s).actions
