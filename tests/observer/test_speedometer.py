import json

import pytest

from scc.observer.claude_code_hooks import append_hook_message
from scc.observer.speedometer import collect_snapshot
from scc.observer.statusline import append_statusline_sample


def make_run(tmp_path, *, hard_q="1.0", soft_q="0.5", q_min="0.9"):
    task_dir = tmp_path / "task"
    verifier_dir = task_dir / "verifiers"
    verifier_dir.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (verifier_dir / "hard.sh").write_text(f"#!/bin/sh\nprintf 'q={hard_q}\\n'\n")
    (verifier_dir / "soft.sh").write_text(f"#!/bin/sh\nprintf 'q={soft_q}\\n'\n")
    (task_dir / "goal.yaml").write_text(
        f"q_min: {q_min}\nrequirements:\n"
        "  - id: build\n    weight: 0.5\n    hard: true\n    verifier: verifiers/hard.sh\n"
        "  - id: tests\n    weight: 0.5\n    hard: false\n    verifier: verifiers/soft.sh\n"
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "config.json").write_text(json.dumps({
        "run_id": "test-run",
        "task_dir": str(task_dir),
        "workspace": str(workspace),
    }))
    return run_dir


def test_verifiers_drive_weighted_completion_and_goal(tmp_path):
    snapshot = collect_snapshot(make_run(tmp_path))
    assert snapshot["progress"] == pytest.approx(0.75)
    assert snapshot["completion_distance"] == pytest.approx(0.25)
    assert not snapshot["goal_reached"]
    assert snapshot["requirements"][0]["q"] == 1.0
    assert snapshot["context_usage"] is None
    assert snapshot["uncertainty"] is None


def test_hard_failure_blocks_goal_even_at_q_min(tmp_path):
    snapshot = collect_snapshot(make_run(tmp_path, hard_q="0.0", soft_q="1.0", q_min="0.5"))
    assert snapshot["progress"] == pytest.approx(0.5)
    assert not snapshot["goal_reached"]


def test_session_events_do_not_change_verified_progress(tmp_path):
    run_dir = make_run(tmp_path)
    first = collect_snapshot(run_dir)
    with (run_dir / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({
            "kind": "session_event",
            "payload": {"event_name": "PostToolUse", "tool_name": "Write"},
        }) + "\n")
    second = collect_snapshot(run_dir)
    assert second["progress"] == first["progress"]
    assert second["session_event_count"] == 1
    assert second["session_events_by_type"] == {"PostToolUse": 1}


def test_prompt_and_context_observations_do_not_change_verified_progress(tmp_path):
    run_dir = make_run(tmp_path)
    append_hook_message(
        run_dir,
        "UserPromptSubmit",
        json.dumps({
            "session_id": "session-1",
            "prompt": "Создай игру. Без звука. Результат: файл. Тесты должны пройти.",
        }),
    )
    append_statusline_sample(run_dir, {
        "session_id": "session-1",
        "context_window": {
            "total_input_tokens": 1000,
            "context_window_size": 100000,
            "used_percentage": 1,
            "remaining_percentage": 99,
        },
    })
    snapshot = collect_snapshot(run_dir)

    assert snapshot["progress"] == pytest.approx(0.75)
    assert snapshot["latest_prompt_completeness"]["score"] == pytest.approx(1.0)
    assert snapshot["context_usage"]["used_percentage"] == 1
    assert snapshot["context_usage"]["stale"] is False


def test_invalid_verifier_path_gets_zero_and_cannot_escape_task(tmp_path):
    run_dir = make_run(tmp_path)
    config = json.loads((run_dir / "config.json").read_text())
    goal_path = tmp_path / "task" / "goal.yaml"
    goal_path.write_text(
        "q_min: 0.9\nrequirements:\n"
        "  - id: build\n    weight: 1.0\n    hard: true\n    verifier: ../outside.sh\n"
    )
    snapshot = collect_snapshot(run_dir)
    assert snapshot["progress"] == 0.0
    assert snapshot["requirements"][0]["status"] == "invalid verifier path"
