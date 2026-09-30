from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scc.log_explorer.catalog import filter_records, list_runs, page_records
from scc.log_explorer.cli import main
from scc.log_explorer.process_log import MAX_LINE_BYTES, read_process_log_page
from scc.log_explorer.query import QueryError, parse_query
from scc.log_explorer.reader import discover_runs, load_run
from scc.log_explorer import ui


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_jsonl(path: Path, *values: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")


def make_run(root: Path, run_id: str, *, status: dict | None = None, started_at: float = 9999999999) -> Path:
    run = root / run_id
    run.mkdir(parents=True)
    write_json(run / "config.json", {"run_id": run_id, "started_at": started_at, "workspace": "/private/workspace", "unknown_secret": "MUST_NOT_RENDER"})
    if status is not None:
        write_json(run / "status.json", status)
    return run


def event(ts: float, name: str, *, session: str = "session-1", tool: str | None = None, extra: dict | None = None) -> dict:
    payload = {"event_name": name, "session_id": session}
    if tool:
        payload["tool_name"] = tool
    if extra:
        payload.update(extra)
    return {"kind": "session_event", "node_id": "run-1", "payload": payload, "ts": ts, "tokens": 0}


def test_discovery_is_direct_only_skips_symlinks_and_sorts_by_activity(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()
    late = make_run(root, "late", status={"state": "stopped", "updated_at": 30})
    tie_b = make_run(root, "tie-b", status={"state": "stopped", "updated_at": 20})
    tie_a = make_run(root, "tie-a", status={"state": "stopped", "updated_at": 20})
    no_time = make_run(root, "no-time")
    (no_time / "config.json").write_text(json.dumps({"run_id": "no-time", "started_at": 9999999999}), encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    make_run(nested, "hidden")
    outside = tmp_path / "outside"
    outside.mkdir()
    make_run(outside, "linked")
    try:
        (root / "outside-link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pass

    runs = discover_runs(root)
    assert [run.run_id for run in runs] == ["late", "tie-a", "tie-b", "nested", "no-time"]
    assert all(run.run_id != "hidden" for run in runs)
    assert runs[-1].last_activity is None


def test_partial_run_malformed_and_unsupported_rows_are_visible(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "partial")
    (run / "events.jsonl").write_bytes(b'{bad json}\n[]\n' + json.dumps(event(1, "PostToolUse")).encode() + b"\n" + bytes([255, 10]))
    (run / "context_samples.jsonl").write_text("", encoding="utf-8")

    loaded = load_run(run)
    event_records = [record for record in loaded.records if record.source == "events" and record.line > 0]
    by_line = {record.line: record.issue for record in event_records}
    assert by_line == {1: "parse error", 2: "unsupported record", 3: None, 4: "parse error"}
    assert [record.line for record in event_records] == [3, 1, 2, 4]
    assert "messages.jsonl: missing" in loaded.issues
    assert "context_samples.jsonl: empty" in loaded.issues
    assert any(record.file == "messages.jsonl" and record.issue == "missing" for record in loaded.records)
    assert any(record.file == "context_samples.jsonl" and record.issue == "empty" for record in loaded.records)
    assert loaded.observer_state != "running"
    assert loaded.task_lifecycle == "unknown"


def test_symlinked_data_files_are_not_followed(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "symlinked")
    outside = tmp_path / "outside.jsonl"
    outside.write_text(json.dumps({"kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit", "text": "OUTSIDE_PRIVATE_DATA", "text_status": "ok"}), encoding="utf-8")
    try:
        (run / "messages.jsonl").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not supported")

    loaded = load_run(run)
    assert "OUTSIDE_PRIVATE_DATA" not in repr(loaded.records)
    assert "messages.jsonl: unavailable or unsafe" in loaded.issues


def test_allowlist_never_exposes_unknown_fields_or_tool_payloads(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "privacy")
    write_jsonl(run / "events.jsonl", event(1, "PostToolUse", tool="Read", extra={"tool_input": "PRIVATE_TOOL_PAYLOAD", "api_body": "PRIVATE_API_BODY"}))
    write_jsonl(run / "messages.jsonl", {
        "kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit", "session_id": "s1", "ts": 2,
        "text": "find collision [REDACTED]", "redactions": 1, "truncated": True, "text_status": "ok",
        "tool_input": "PRIVATE_TOOL_PAYLOAD", "hidden_instruction": "PRIVATE_SYSTEM_TEXT",
    }, {"kind": "conversation_message", "role": "assistant", "event_name": "PostToolUse", "ts": 3, "text": "NOT A STOP RESPONSE", "text_status": "ok"})
    write_jsonl(run / "snapshots.jsonl", {"ts": 3, "progress": 0.72, "completion_distance": 0.28, "goal_reached": False, "requirements": [{"id": "tests", "q": 0.5, "weight": 1, "hard": True, "status": "ok", "private": "NO"}], "unknown": "SECRET"})

    loaded = load_run(run)
    serialized = repr(loaded.config) + repr([r.fields for r in loaded.records]) + " ".join(r.searchable for r in loaded.records)
    assert "MUST_NOT_RENDER" not in serialized
    assert "PRIVATE_TOOL_PAYLOAD" not in serialized
    assert "PRIVATE_API_BODY" not in serialized
    assert "PRIVATE_SYSTEM_TEXT" not in serialized
    assert "NOT A STOP RESPONSE" not in serialized
    assert "SECRET" not in serialized
    message = next(row for row in loaded.records if row.source == "messages")
    assert message.searchable == "find collision [REDACTED]"
    assert message.redactions == 1 and message.truncated
    assert loaded.progress == pytest.approx(0.72)
    assert loaded.goal_reached is False


def test_timeline_tie_break_and_pagination_are_stable(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "order")
    write_jsonl(run / "snapshots.jsonl", {"ts": 5, "progress": 0.5})
    write_jsonl(run / "messages.jsonl", {"kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit", "ts": 5, "text": "hello", "text_status": "ok"})
    write_jsonl(run / "events.jsonl", event(5, "PostToolUse"), event(5, "SessionEnd"))

    records = load_run(run).records
    timestamped = [record for record in records if record.ts == 5]
    assert [(r.source, r.line) for r in timestamped] == [
        ("events", 1), ("events", 2), ("messages", 1), ("snapshots", 1),
    ]
    assert any(record.file == "context_samples.jsonl" and record.issue == "missing" for record in records)
    first_page = page_records(timestamped, 0, 2)
    second_page = page_records(timestamped, 2, 2)
    assert first_page.total == second_page.total == 4
    assert len(first_page.records) == len(second_page.records) == 2
    assert first_page.records[0].identity != second_page.records[0].identity


def test_query_filters_are_allowlisted_and_anded(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "query")
    write_jsonl(run / "events.jsonl", event(10, "PostToolUse", tool="Write"), event(20, "SessionEnd", tool="Read"))
    write_jsonl(run / "messages.jsonl", {"kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit", "ts": 11, "session_id": "session-1", "text": "Add collision handling", "text_status": "ok"})
    write_jsonl(run / "snapshots.jsonl", {"ts": 12, "progress": 0.4, "goal_reached": False, "requirements": [{"id": "tests", "status": "failed", "q": 0}]})
    records = load_run(run).records

    result = filter_records(records, parse_query('source:events type:PostToolUse session:session-1 tool:Write after:1970-01-01T00:00:09Z before:1970-01-01T00:00:11Z'))
    assert len(result) == 1 and result[0].fields["tool_name"] == "Write"
    assert len(filter_records(records, parse_query("collision"))) == 1
    assert len(filter_records(records, parse_query("tool_input"))) == 0
    assert len(filter_records(records, parse_query("requirement:tests status:failed"))) == 1


@pytest.mark.parametrize("text", ["private_field:value", "source:", '"unclosed', "after:not-a-date"])
def test_invalid_queries_are_rejected(text: str) -> None:
    with pytest.raises(QueryError):
        parse_query(text)


def test_only_verifier_snapshot_drives_progress_and_lifecycle_stays_unknown(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "semantics", status={"state": "stopped", "updated_at": 12})
    write_jsonl(run / "events.jsonl", event(10, "SessionStart"), event(11, "PostToolUseFailure"))
    write_jsonl(run / "messages.jsonl", {"kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit", "ts": 11.5, "text": "done", "text_status": "ok"})
    loaded = load_run(run)
    assert loaded.observer_state == "stopped"
    assert loaded.task_lifecycle == "running"
    assert loaded.progress is None
    assert loaded.goal_reached is None

    write_jsonl(run / "events.jsonl", event(13, "SessionEnd"))
    loaded = load_run(run)
    assert loaded.task_lifecycle == "unknown"
    assert loaded.progress is None


def test_browse_search_and_filter_do_not_mutate_source_files(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    run = make_run(root, "immutable", status={"state": "stopped", "updated_at": 4})
    write_jsonl(run / "events.jsonl", event(1, "PostToolUse", tool="Read"))
    write_jsonl(run / "messages.jsonl", {"kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit", "ts": 2, "text": "searchable prompt", "text_status": "ok"})
    write_jsonl(run / "context_samples.jsonl", {"kind": "context_sample", "ts": 3, "used_percentage": 35})
    write_jsonl(run / "snapshots.jsonl", {"ts": 4, "progress": 0.5, "goal_reached": False})
    before = _hash_tree(root)

    runs = list_runs(str(root))
    records = runs[0].records
    filter_records(records, parse_query("searchable"))
    filter_records(records, parse_query("source:events"))
    discover_runs(root)

    assert _hash_tree(root) == before


def test_cli_list_shows_catalog_without_modifying_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "runs"
    make_run(root, "cli", status={"state": "stopped", "updated_at": 5})
    before = _hash_tree(root)
    assert main(["--runs-dir", str(root), "--list"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("cli\t")
    assert "stopped" in output and "unknown" in output and "unavailable" in output
    assert _hash_tree(root) == before


def test_ui_handles_resize_refresh_and_quit_without_filesystem_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "runs"
    make_run(root, "ui", status={"state": "stopped", "updated_at": 1})
    before = _hash_tree(root)

    class FakeScreen:
        keys = [ui.curses.KEY_RESIZE, ord("r"), ord("q")]
        def keypad(self, _enabled: bool) -> None: pass
        def erase(self) -> None: pass
        def getmaxyx(self) -> tuple[int, int]: return 24, 100
        def addnstr(self, *_args) -> None: pass
        def refresh(self) -> None: pass
        def getch(self) -> int: return self.keys.pop(0)

    monkeypatch.setattr(ui.curses, "curs_set", lambda _value: None)
    ui.run_ui(FakeScreen(), root)
    assert _hash_tree(root) == before


def test_ui_accepts_allowlisted_query_and_displays_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "runs"
    run = make_run(root, "search-ui", status={"state": "stopped", "updated_at": 1})
    write_jsonl(run / "messages.jsonl", {"kind": "conversation_message", "role": "user", "event_name": "UserPromptSubmit", "ts": 1, "text": "allowed prompt", "text_status": "ok"})

    class QueryScreen:
        keys = [10, ord("/"), ord("q")]
        query_keys = list("source:messages") + ["\n"]
        lines: list[str] = []
        def keypad(self, _enabled: bool) -> None: pass
        def erase(self) -> None: pass
        def getmaxyx(self) -> tuple[int, int]: return 24, 100
        def addnstr(self, _row, _col, text, _length) -> None: self.lines.append(text)
        def refresh(self) -> None: pass
        def move(self, _row: int, _col: int) -> None: pass
        def getch(self) -> int: return self.keys.pop(0)
        def get_wch(self) -> str: return self.query_keys.pop(0)

    monkeypatch.setattr(ui.curses, "curs_set", lambda _value: None)
    screen = QueryScreen()
    ui.run_ui(screen, root)
    assert any("Query: source:messages" in line for line in screen.lines)


def test_process_log_search_streams_matches_and_pages_from_newest(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "worker-log")
    (run / "speedometer.log").write_text("boot\nerror first\nhealthy\nERROR second\n", encoding="utf-8")
    query = parse_query("source:speedometer.log error")

    newest = read_process_log_page(run, "worker-log", query, page_size=1)
    older = read_process_log_page(run, "worker-log", query, page_index=1, page_size=1)
    assert newest.total == 2 and newest.page_count == 2
    assert [(r.line, r.searchable) for r in newest.records] == [(4, "ERROR second")]
    assert [(r.line, r.searchable) for r in older.records] == [(2, "error first")]


def test_process_log_distinguishes_missing_empty_symlink_and_caps_long_lines(tmp_path: Path) -> None:
    run = make_run(tmp_path / "runs", "worker-log-states")
    query = parse_query("")
    assert read_process_log_page(run, "worker-log-states", query).issue == "missing"

    log_path = run / "speedometer.log"
    log_path.write_bytes(b"")
    assert read_process_log_page(run, "worker-log-states", query).issue == "empty"

    log_path.write_bytes(b"visible " + b"x" * (MAX_LINE_BYTES + 100) + b" tail\n")
    page = read_process_log_page(run, "worker-log-states", query)
    assert len(page.records) == 1 and page.records[0].line == 1
    assert page.records[0].truncated
    assert len(page.records[0].searchable.encode("utf-8")) <= MAX_LINE_BYTES

    outside = tmp_path / "outside.log"
    outside.write_text("private text", encoding="utf-8")
    log_path.unlink()
    try:
        log_path.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not supported")
    assert read_process_log_page(run, "worker-log-states", query).issue == "unsafe symlink"


def test_process_log_queries_do_not_modify_the_log(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    run = make_run(root, "worker-log-immutable")
    (run / "speedometer.log").write_text("boot\nerror\nfinished\n", encoding="utf-8")
    before = _hash_tree(root)

    page = read_process_log_page(run, "worker-log-immutable", parse_query("error"))
    assert [record.searchable for record in page.records] == ["error"]
    assert _hash_tree(root) == before


def test_ui_opens_and_searches_process_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "runs"
    run = make_run(root, "worker-ui", status={"state": "stopped", "updated_at": 1})
    (run / "speedometer.log").write_text("boot\nverifier error: missing file\n", encoding="utf-8")

    class LogScreen:
        keys = [10, ord("l"), ord("/"), 10, 10, ord("q")]
        query_keys = list("source:speedometer.log error") + ["\n"]
        lines: list[str] = []
        def keypad(self, _enabled: bool) -> None: pass
        def erase(self) -> None: pass
        def getmaxyx(self) -> tuple[int, int]: return 24, 100
        def addnstr(self, _row, _col, text, _length) -> None: self.lines.append(text)
        def refresh(self) -> None: pass
        def move(self, _row: int, _col: int) -> None: pass
        def getch(self) -> int: return self.keys.pop(0)
        def get_wch(self) -> str: return self.query_keys.pop(0)

    monkeypatch.setattr(ui.curses, "curs_set", lambda _value: None)
    screen = LogScreen()
    ui.run_ui(screen, root)
    assert any("Raw worker text" in line for line in screen.lines)
    assert any("Query: source:speedometer.log error" in line for line in screen.lines)
    assert any("raw worker log line" in line for line in screen.lines)
    assert any("verifier error: missing file" in line for line in screen.lines)


def _hash_tree(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
