import json
import time
from pathlib import Path

from scc.observer import speedometer


def make_task(root: Path) -> Path:
    task = root / "task"
    verifier_dir = task / "verifiers"
    verifier_dir.mkdir(parents=True)
    (verifier_dir / "check.sh").write_text("#!/bin/sh\nprintf 'q=1.0\\n'\n")
    (task / "goal.yaml").write_text(
        "q_min: 0.9\nrequirements:\n"
        "  - id: acceptance\n    weight: 1.0\n    hard: true\n    verifier: verifiers/check.sh\n"
    )
    return task


def test_background_start_status_watch_and_stop(tmp_path, monkeypatch, capsys):
    task = make_task(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runs = tmp_path / "runs"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(speedometer, "RUNS_DIR", runs)

    assert speedometer.main([
        "start", "--run-id", "life-cycle", "--task-dir", str(task),
        "--workspace", str(workspace), "--interval", "1", "--background",
    ]) == 0
    run_dir = runs / "life-cycle"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not (run_dir / "snapshots.jsonl").exists():
        time.sleep(0.05)
    assert (run_dir / "snapshots.jsonl").exists()

    assert speedometer.main(["status", "--run-id", "life-cycle"]) == 0
    status_output = capsys.readouterr().out
    assert "state: running" in status_output
    assert "verified progress: 100.0%" in status_output

    assert "verified 100%" in speedometer._render("life-cycle")
    assert speedometer.main(["stop", "--run-id", "life-cycle"]) == 0
    assert speedometer._pid_state(run_dir)[0] != "running"


def test_hook_install_and_uninstall_preserve_unrelated_settings(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(speedometer, "RUNS_DIR", tmp_path / "runs")
    run_dir = tmp_path / "runs" / "demo"
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(json.dumps({"run_id": "demo", "workspace": str(workspace)}))

    settings_path = workspace / ".claude" / "settings.local.json"
    settings_path.parent.mkdir()
    settings_path.write_text(json.dumps({
        "permissions": {"defaultMode": "default"},
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "existing-hook"}]}]},
    }))

    assert speedometer.main(["hooks", "install", "--run-id", "demo"]) == 0
    settings = json.loads(settings_path.read_text())
    assert settings["permissions"]["defaultMode"] == "default"
    assert any("scc-speedometer-managed:demo" in json.dumps(entry) for entries in settings["hooks"].values() for entry in entries)
    assert any("existing-hook" in json.dumps(entry) for entry in settings["hooks"]["Stop"])

    assert speedometer.main(["hooks", "uninstall", "--run-id", "demo"]) == 0
    settings = json.loads(settings_path.read_text())
    assert settings["permissions"]["defaultMode"] == "default"
    assert settings["hooks"] == {"Stop": [{"hooks": [{"type": "command", "command": "existing-hook"}]}]}


def test_stale_pid_is_reported_without_signalling(tmp_path, monkeypatch, capsys):
    run_dir = tmp_path / "stale-run"
    run_dir.mkdir()
    (run_dir / "speedometer.pid.json").write_text(json.dumps({"pid": 987654321}))
    monkeypatch.setattr(speedometer, "RUNS_DIR", tmp_path)

    def no_process(_pid, _signal):
        raise ProcessLookupError

    monkeypatch.setattr(speedometer.os, "kill", no_process)
    assert speedometer._pid_state(run_dir) == ("stale", None)
    assert speedometer._stop("stale-run") == 1
    assert "state=stale" in capsys.readouterr().out


def test_statusline_install_uninstall_preserves_workspace_hooks(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(speedometer, "RUNS_DIR", tmp_path / "runs")
    run_dir = tmp_path / "runs" / "ctx-run"
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(json.dumps({"run_id": "ctx-run", "workspace": str(workspace)}))
    settings_path = workspace / ".claude" / "settings.local.json"
    settings_path.parent.mkdir()
    settings_path.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "keep-me"}]}]}}))

    assert speedometer.main(["statusline", "install", "--run-id", "ctx-run"]) == 0
    settings = json.loads(settings_path.read_text())
    assert settings["statusLine"]["type"] == "command"
    assert "scc.observer.statusline" in settings["statusLine"]["command"]
    assert settings["hooks"]["Stop"][0]["hooks"][0]["command"] == "keep-me"

    assert speedometer.main(["statusline", "uninstall", "--run-id", "ctx-run"]) == 0
    settings = json.loads(settings_path.read_text())
    assert "statusLine" not in settings
    assert settings["hooks"]["Stop"][0]["hooks"][0]["command"] == "keep-me"


def test_statusline_install_refuses_to_replace_existing_entry(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_dir = tmp_path / "runs" / "conflict"
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(json.dumps({"run_id": "conflict", "workspace": str(workspace)}))
    settings_path = workspace / ".claude" / "settings.local.json"
    settings_path.parent.mkdir()
    settings_path.write_text(json.dumps({"statusLine": {"type": "command", "command": "existing-statusline"}}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(speedometer, "RUNS_DIR", tmp_path / "runs")

    assert speedometer.main(["statusline", "install", "--run-id", "conflict"]) == 2
    assert json.loads(settings_path.read_text())["statusLine"]["command"] == "existing-statusline"
    assert "refusing to replace" in capsys.readouterr().err


def test_prepare_creates_root_context_import_without_game_code(tmp_path, monkeypatch):
    task = make_task(tmp_path)
    (task / "context").mkdir()
    (task / "context" / "CLAUDE.md").write_text("# approved Snake context\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(speedometer, "RUNS_DIR", tmp_path / "runs")

    assert speedometer.main(["prepare", "--run-id", "fresh", "--task-dir", str(task)]) == 0
    workspace = tmp_path / "runs" / "fresh" / "workspace"
    assert (workspace / "CLAUDE.md").read_text().splitlines() == [
        "# Snake measurement workspace", "", "@demos/snake/context/CLAUDE.md",
    ]
    assert (workspace / "demos/snake/context/CLAUDE.md").read_text() == "# approved Snake context\n"
    assert (workspace / "demos/snake/rules").is_dir()
    assert not (workspace / "demos/snake/game.py").exists()


def test_start_refuses_to_reuse_an_existing_run_id(tmp_path, monkeypatch, capsys):
    task = make_task(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runs = tmp_path / "runs"
    old_run = runs / "same-id"
    old_run.mkdir(parents=True)
    (old_run / "config.json").write_text(json.dumps({"run_id": "same-id"}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(speedometer, "RUNS_DIR", runs)

    result = speedometer.main([
        "start", "--run-id", "same-id", "--task-dir", str(task), "--workspace", str(workspace),
    ])
    assert result == 2
    assert "choose a new run id" in capsys.readouterr().err
