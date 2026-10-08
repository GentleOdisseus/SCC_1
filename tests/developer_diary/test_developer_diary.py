from __future__ import annotations

import hashlib
import importlib.util
import json
import shlex
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest


_TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "developer_diary.py"
_SPEC = importlib.util.spec_from_file_location("developer_diary", _TOOL_PATH)
assert _SPEC is not None and _SPEC.loader is not None
diary = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(diary)


def _feed(monkeypatch: pytest.MonkeyPatch, event_name: str, payload: dict, root: Path, *, scope: str = "project", run_id: str | None = None) -> None:
    monkeypatch.setattr(diary.sys, "stdin", StringIO(json.dumps(payload)))
    assert diary.capture_message(event_name, scope, run_id, root) == 0


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_capture_only_keeps_visible_prompt_and_final_stop_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "developer_diary"
    root.mkdir()
    session = "synthetic-session"
    capture_dir = diary._capture_directory(root, "project", session)

    _feed(monkeypatch, "UserPromptSubmit", {
        "session_id": session,
        "prompt_id": "p-1",
        "prompt": "Please inspect api_key=abcdef1234567890 and <script>alert(1)</script> [31mred[0m",
        "tool_input": {"private": "NEVER_CAPTURE_TOOL_PAYLOAD"},
    }, root)
    _feed(monkeypatch, "Stop", {
        "session_id": session,
        "prompt_id": "p-1",
        "last_assistant_message": "Final visible answer.",
        "tool_response": {"private": "NEVER_CAPTURE_TOOL_OUTPUT"},
    }, root)

    records = _jsonl(capture_dir / "messages.jsonl")
    assert [record["role"] for record in records] == ["user", "assistant"]
    assert records[0]["redactions"] == 1
    assert "abcdef1234567890" not in json.dumps(records, ensure_ascii=False)
    serialized = json.dumps(records, ensure_ascii=False)
    assert "NEVER_CAPTURE_TOOL_PAYLOAD" not in serialized
    assert "NEVER_CAPTURE_TOOL_OUTPUT" not in serialized
    pages = list((root / "sessions").glob("*.md"))
    assert len(pages) == 1
    rendered = pages[0].read_text(encoding="utf-8")
    assert "Final visible answer." in rendered
    assert "&lt;script&gt;" in rendered
    assert "\\u001b[31m" in rendered
    assert "\x1b" not in rendered
    assert "redacted: 1" in rendered
    assert "NEVER_CAPTURE_TOOL_" not in rendered


def test_missing_hook_identifiers_are_marked_unmatched_without_guessing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "developer_diary"
    root.mkdir()
    _feed(monkeypatch, "Stop", {"last_assistant_message": "answer without identifiers"}, root)
    capture_dir = diary._capture_directory(root, "project", None)
    record = _jsonl(capture_dir / "messages.jsonl")[0]
    assert record["turn_index"] is None
    assert record["turn_status"] == "unmatched_no_session_id"
    rendered = next((root / "sessions").glob("*.md")).read_text(encoding="utf-8")
    assert "Session: `unavailable`" in rendered
    assert "turn: `unavailable`" in rendered


def test_capture_with_speedometer_scope_does_not_touch_run_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "developer_diary"
    root.mkdir()
    run_id = "synthetic-run"
    run_dir = tmp_path / "experiments" / "runs" / run_id
    run_dir.mkdir(parents=True)
    run_files = {
        run_dir / "events.jsonl": b"unchanged events\n",
        run_dir / "messages.jsonl": b"unchanged run feed\n",
        run_dir / "snapshots.jsonl": b"unchanged snapshots\n",
    }
    for path, content in run_files.items():
        path.write_bytes(content)
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in run_files}

    _feed(monkeypatch, "UserPromptSubmit", {
        "session_id": "speedometer-session",
        "prompt_id": "p-2",
        "prompt": "A test prompt.",
    }, root, scope="speedometer", run_id=run_id)

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in run_files}
    capture_files = list((root / "captures" / "speedometer" / run_id).rglob("messages.jsonl"))
    assert before == after
    assert len(capture_files) == 1
    assert _jsonl(capture_files[0])[0]["text"] == "A test prompt."


def test_capture_deduplicates_prompt_id_and_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "developer_diary"
    root.mkdir()
    payload = {"session_id": "session", "prompt_id": "p-1", "prompt": "same prompt"}
    _feed(monkeypatch, "UserPromptSubmit", payload, root)
    _feed(monkeypatch, "UserPromptSubmit", payload, root)
    capture_dir = diary._capture_directory(root, "project", "session")
    records = _jsonl(capture_dir / "messages.jsonl")
    assert len(records) == 1


def test_hook_install_and_uninstall_preserve_unrelated_settings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings_path = workspace / ".claude" / "settings.local.json"
    settings_path.parent.mkdir()
    original = {
        "permissions": {"defaultMode": "default"},
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "existing-hook"}]}]},
        "statusLine": {"type": "command", "command": "existing-statusline"},
    }
    settings_path.write_text(json.dumps(original), encoding="utf-8")

    assert diary.install_hooks(workspace) == 0
    installed = json.loads(settings_path.read_text(encoding="utf-8"))
    assert installed["permissions"] == original["permissions"]
    assert installed["statusLine"] == original["statusLine"]
    assert any("existing-hook" in json.dumps(item) for item in installed["hooks"]["Stop"])
    diary_entries = [
        item
        for entries in installed["hooks"].values()
        for item in entries
        if any(diary._contains_marker(item, diary._marker("project", event)) for event in diary.HOOK_EVENTS)
    ]
    assert len(diary_entries) == 2

    assert diary.install_hooks(workspace) == 0
    installed_twice = json.loads(settings_path.read_text(encoding="utf-8"))
    assert len([
        item
        for entries in installed_twice["hooks"].values()
        for item in entries
        if any(diary._contains_marker(item, diary._marker("project", event)) for event in diary.HOOK_EVENTS)
    ]) == 2

    assert diary.uninstall_hooks(workspace) == 0
    removed = json.loads(settings_path.read_text(encoding="utf-8"))
    assert removed["permissions"] == original["permissions"]
    assert removed["statusLine"] == original["statusLine"]
    assert removed["hooks"] == original["hooks"]
    assert "Installed local developer diary hooks" in capsys.readouterr().out


def test_installed_local_hooks_capture_synthetic_project_turn_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    diary_root = tmp_path / "developer_diary"
    diary_root.mkdir()
    monkeypatch.setattr(diary, "DIARY_ROOT", diary_root)

    assert diary.install_hooks(workspace) == 0
    settings = json.loads((workspace / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    commands = {}
    for event_name in diary.HOOK_EVENTS:
        entry = next(
            item for item in settings["hooks"][event_name]
            if any(isinstance(hook, dict) and hook.get("statusMessage", "").startswith(diary.HOOK_MARKER) for hook in item.get("hooks", []))
        )
        commands[event_name] = shlex.split(entry["hooks"][0]["command"])

    session_id = "end-to-end-session"
    events = [
        ("UserPromptSubmit", {"session_id": session_id, "prompt_id": "p-1", "prompt": "synthetic project prompt"}),
        ("Stop", {"session_id": session_id, "prompt_id": "p-1", "last_assistant_message": "synthetic final answer"}),
    ]
    for event_name, payload in events:
        result = subprocess.run(commands[event_name], input=json.dumps(payload), text=True, capture_output=True, check=False)
        assert result.returncode == 0
        assert "synthetic project prompt" not in result.stdout + result.stderr
        assert "synthetic final answer" not in result.stdout + result.stderr

    capture_dir = diary._capture_directory(diary_root, "project", session_id)
    records = _jsonl(capture_dir / "messages.jsonl")
    assert [record["role"] for record in records] == ["user", "assistant"]
    rendered = next((diary_root / "sessions").glob("*.md")).read_text(encoding="utf-8")
    assert "synthetic project prompt" in rendered
    assert "synthetic final answer" in rendered
    assert not (diary_root / "commits.md").exists(), "capture must not run sync or write commit history"


def test_installed_speedometer_workspace_hook_uses_separate_diary_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "speedometer-workspace"
    workspace.mkdir()
    diary_root = tmp_path / "developer_diary"
    diary_root.mkdir()
    run_id = "selected-run"
    monkeypatch.setattr(diary, "DIARY_ROOT", diary_root)

    assert diary.install_hooks(workspace, run_id=run_id) == 0
    settings = json.loads((workspace / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    entry = next(
        item for item in settings["hooks"]["UserPromptSubmit"]
        if any(isinstance(hook, dict) and hook.get("statusMessage", "").startswith(diary.HOOK_MARKER) for hook in item.get("hooks", []))
    )
    command = shlex.split(entry["hooks"][0]["command"])
    payload = {"session_id": "run-session", "prompt_id": "run-prompt", "prompt": "speedometer workspace prompt"}
    result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, check=False)

    assert result.returncode == 0
    messages = list((diary_root / "captures" / "speedometer" / run_id).rglob("messages.jsonl"))
    assert len(messages) == 1
    assert _jsonl(messages[0])[0]["text"] == "speedometer workspace prompt"
    assert not (tmp_path / "speedometer-workspace" / "messages.jsonl").exists()


def test_install_refuses_unsafe_workspace_settings_symlink(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside-settings.json"
    outside.write_text("{}", encoding="utf-8")
    (workspace / ".claude").mkdir()
    try:
        (workspace / ".claude" / "settings.local.json").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not supported")

    with pytest.raises(ValueError, match="unsafe settings path"):
        diary.install_hooks(workspace)
    assert outside.read_text(encoding="utf-8") == "{}"


def test_sync_renders_commits_separately_and_preserves_manual_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "developer_diary"
    root.mkdir()
    notes = root / "notes.md"
    notes.write_text("# My note\nKeep this text.\n", encoding="utf-8")
    capture_dir = diary._capture_directory(root, "project", "s1")
    capture_dir.mkdir(parents=True)
    (capture_dir / "messages.jsonl").write_text(json.dumps({
        "kind": "conversation_message",
        "role": "user",
        "event_name": "UserPromptSubmit",
        "session_id": "s1",
        "prompt_id": "p-1",
        "turn_index": 1,
        "turn_status": "matched_by_prompt_id",
        "ts": 1790800000.0,
        "text": "synthetic visible prompt",
        "text_status": "ok",
        "redactions": 0,
        "truncated": False,
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(diary, "_read_commits", lambda _repo: [{
        "hash": "a" * 40,
        "date": "2026-10-01T00:00:00Z",
        "subject": "synthetic commit",
        "files": ["src/example.py"],
    }])

    session_count, commit_count = diary.sync_diary(root, tmp_path)

    assert session_count == 1
    assert commit_count == 1
    assert notes.read_text(encoding="utf-8") == "# My note\nKeep this text.\n"
    session_pages = list((root / "sessions").glob("*.md"))
    assert len(session_pages) == 1
    session_text = session_pages[0].read_text(encoding="utf-8")
    assert "synthetic visible prompt" in session_text
    assert diary._format_timestamp(1790800000.0) in session_text
    commits = (root / "commits.md").read_text(encoding="utf-8")
    assert "synthetic commit" in commits
    assert "synthetic visible prompt" not in commits

    diary.sync_diary(root, tmp_path)
    assert len(list((root / "sessions").glob("*.md"))) == 1
    assert notes.read_text(encoding="utf-8") == "# My note\nKeep this text.\n"


def test_commit_section_escapes_table_cells_and_filters_diary_only_commit() -> None:
    text = diary._render_commits([
        {"hash": "b" * 40, "date": "2026-10-01T00:00:00Z", "subject": "safe | subject", "files": ["src/a.py"]},
    ])
    assert "safe &#124; subject" in text
    assert "developer_diary/" not in text
    commits = [{"hash": "c" * 40, "files": ["developer_diary/notes.md"]}]
    kept: list[dict] = []
    diary._keep_commit(kept, commits[0])
    assert kept == []


def test_git_commit_projection_reads_metadata_in_separate_local_repo(tmp_path: Path) -> None:
    repo = tmp_path / "git-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Diary Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "diary-test@example.invalid"], check=True)
    source = repo / "example.txt"
    source.write_text("synthetic file\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "example.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "synthetic commit subject"], check=True)

    commits = diary._read_commits(repo)

    assert len(commits) == 1
    assert commits[0]["subject"] == "synthetic commit subject"
    assert commits[0]["files"] == ["example.txt"]
    assert commits[0]["date"].endswith("Z")


def test_preview_reports_counts_without_exposing_message_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "developer_diary"
    root.mkdir()
    capture_dir = diary._capture_directory(root, "project", "preview-session")
    capture_dir.mkdir(parents=True)
    (capture_dir / "messages.jsonl").write_text(json.dumps({
        "kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit",
        "session_id": "preview-session", "ts": 1790800000.0, "text": "NEVER_PRINT_THIS_PROMPT", "text_status": "ok",
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(diary, "_read_commits", lambda _root: [])

    counts = diary.preview_sync(root, tmp_path)

    assert counts == (1, 0)
