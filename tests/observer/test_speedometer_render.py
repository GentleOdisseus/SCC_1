import json
import time

from scc.observer import speedometer


def test_display_text_strips_terminal_controls_and_marks_unavailable() -> None:
    value = "\x1b[31mred\x1b[0m\x01green\ttext\n"

    assert speedometer._display_text(value) == "red green text"
    assert speedometer._display_text(None) == "[unavailable]"
    assert speedometer._display_text(" \t\n") == "[empty]"


def test_display_text_shortens_long_text_with_visible_marker() -> None:
    rendered = speedometer._display_text("word " * 20, width=14)

    assert rendered.endswith(" …")
    assert len(rendered) <= 14


def test_render_waiting_state_and_observer_error(tmp_path, monkeypatch) -> None:
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "waiting-run"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(speedometer, "RUNS_DIR", runs_dir)
    (run_dir / "status.json").write_text(json.dumps({"state": "error", "error": "verifier unavailable"}))

    rendered = speedometer._render("waiting-run")

    assert rendered.splitlines() == [
        "SCC SPEEDOMETER · waiting-run",
        "Observer error: verifier unavailable",
        "Waiting for first verifier snapshot...",
    ]


def test_render_snapshot_context_events_and_visible_messages(tmp_path, monkeypatch) -> None:
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "render-run"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(speedometer, "RUNS_DIR", runs_dir)

    snapshot = {
        "run_id": "render-run",
        "ts": time.time(),
        "progress": 0.75,
        "completion_distance": 0.25,
        "q_min": 0.9,
        "goal_reached": False,
        "requirements": [{"id": "tests", "q": 0.5, "hard": False, "status": "ok"}],
        "session_event_count": 1,
        "latest_prompt_completeness": {
            "score": 0.5,
            "criteria": {"goal": True, "constraints": False},
        },
        "context_usage": None,
    }
    (run_dir / "snapshots.jsonl").write_text(json.dumps(snapshot) + "\n")
    (run_dir / "events.jsonl").write_text(json.dumps({
        "kind": "session_event",
        "ts": time.time(),
        "payload": {"event_name": "PostToolUse", "tool_name": "Write", "outcome": "success"},
    }) + "\n")
    (run_dir / "messages.jsonl").write_text(json.dumps({
        "role": "user",
        "turn_index": 2,
        "ts": time.time(),
        "text": "Make a safe change",
        "prompt_completeness": snapshot["latest_prompt_completeness"],
    }) + "\n")

    rendered = speedometer._render("render-run")

    assert "IN PROGRESS" in rendered
    assert "verified 75%" in rendered
    assert "tests" in rendered and "50%" in rendered
    assert "Context window: unavailable (StatusLine sample not received)" in rendered
    assert "Latest prompt completeness heuristic: 50%" in rendered
    assert "goal=✓" in rendered and "constraints=·" in rendered
    assert "Session events: 1" in rendered
    assert "PostToolUse Write success" in rendered
    assert "turn 2 User: Make a safe change" in rendered
