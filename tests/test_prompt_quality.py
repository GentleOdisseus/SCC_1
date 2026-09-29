import pytest

from scc.geometry.prompt_quality import assess_prompt


def test_equal_weight_prompt_completeness_detects_all_dimensions():
    result = assess_prompt("Создай игру. Без звука. Результат: файл. Тесты должны пройти.")
    assert result["score"] == pytest.approx(1.0)
    assert all(result["criteria"].values())
    assert result["method"] == "keyword_checklist_heuristic"


def test_incomplete_prompt_shows_missing_checklist_items():
    result = assess_prompt("Исправь змейку")
    assert result["criteria"]["goal"] is True
    assert result["criteria"]["constraints"] is False
    assert result["criteria"]["deliverable"] is True
    assert result["criteria"]["acceptance_checks"] is False
    assert result["score"] == pytest.approx(0.5)


def test_prompt_quality_is_observation_not_task_progress():
    from scc.geometry.distance import progress
    from scc.models import Goal, Requirement

    goal = Goal([Requirement("tests", 1.0, q=0.25)])
    before = progress(goal)
    assess_prompt("Create a tested terminal game with explicit acceptance criteria")
    assert progress(goal) == before
