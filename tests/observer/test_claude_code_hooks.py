import json

import pytest

from scc.observer import claude_code_hooks, speedometer
from scc.observer.claude_code_hooks import append_hook_event, append_hook_message, normalize_hook_payload
from scc.observer.events import EventKind


def test_normalize_hook_payload_keeps_metadata_only():
    event = normalize_hook_payload(
        "PostToolUse",
        json.dumps({
            "session_id": "session-123",
            "tool_name": "Write",
            "tool_input": {"content": "secret prompt payload"},
            "tool_response": {"content": "private file contents"},
        }),
    )

    assert event.kind is EventKind.SESSION_EVENT
    assert event.payload == {
        "event_name": "PostToolUse",
        "session_id": "session-123",
        "tool_name": "Write",
        "outcome": "success",
    }
    assert "secret" not in json.dumps(event.to_dict())
    assert "private" not in json.dumps(event.to_dict())
    assert event.tokens == 0
    assert event.cost_usd == 0.0


def test_failure_event_is_classified():
    event = normalize_hook_payload("PostToolUseFailure", '{"tool_name":"Bash"}')
    assert event.payload["outcome"] == "failure"


@pytest.mark.parametrize("raw", ["not-json", "[]", "null"])
def test_invalid_hook_payload_is_rejected(raw):
    with pytest.raises(ValueError):
        normalize_hook_payload("Stop", raw)


def test_append_hook_event_writes_one_jsonl_record(tmp_path):
    append_hook_event(tmp_path, "SessionStart", '{"session_id":"s-1"}')
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["node_id"] == tmp_path.name
    assert rows[0]["payload"]["event_name"] == "SessionStart"
    assert rows[0]["payload"]["session_id"] == "s-1"


def test_cli_hook_command_reads_stdin_and_appends_event(tmp_path, monkeypatch):
    from io import StringIO

    monkeypatch.setattr(speedometer.sys, "stdin", StringIO('{"session_id":"cli-session"}'))
    assert speedometer.main([
        "hook", "--run-dir", str(tmp_path), "--event-name", "UserPromptSubmit",
    ]) == 0
    row = json.loads((tmp_path / "events.jsonl").read_text())
    assert row["payload"] == {"event_name": "UserPromptSubmit", "session_id": "cli-session"}


def test_unknown_hook_event_is_rejected():
    with pytest.raises(ValueError, match="unsupported hook event"):
        normalize_hook_payload("PreToolUse", "{}")


def test_prompt_and_final_response_are_persisted_separately(tmp_path):
    prompt = json.dumps({
        "session_id": "session-one",
        "prompt_id": "prompt-one",
        "prompt": "Создай игру. Без звука. Результат: файл. Тесты должны пройти.",
        "tool_input": {"content": "must not be saved"},
    })
    response = json.dumps({
        "session_id": "session-one",
        "last_assistant_message": "Добавил основной цикл игры.",
        "tool_response": {"content": "must not be saved"},
    })
    append_hook_message(tmp_path, "UserPromptSubmit", prompt)
    append_hook_message(tmp_path, "Stop", response)

    rows = [json.loads(line) for line in (tmp_path / "messages.jsonl").read_text().splitlines()]
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["turn_index"] == rows[1]["turn_index"] == 1
    assert rows[0]["prompt_completeness"]["score"] == 1.0
    assert rows[0]["text"].startswith("Создай игру")
    assert rows[1]["text"] == "Добавил основной цикл игры."
    serialized = json.dumps(rows, ensure_ascii=False)
    assert "must not be saved" not in serialized
    assert "tool_input" not in serialized


def test_message_secret_redaction_and_64_kib_truncation(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_code_hooks, "load_config", lambda: {"speedometer": {"message_max_bytes": 1024}})
    prompt = "Создай игру. api_key=abcdef1234567890. " + ("text " * 1000)
    append_hook_message(tmp_path, "UserPromptSubmit", json.dumps({"session_id": "s", "prompt": prompt}))
    row = json.loads((tmp_path / "messages.jsonl").read_text())
    assert row["redactions"] == 1
    assert "abcdef1234567890" not in row["text"]
    assert row["truncated"] is True
    assert len(row["text"].encode("utf-8")) <= 1024
    assert row["text"].endswith("...[truncated at 1024 bytes]...")


def test_response_without_prompt_is_marked_unmatched(tmp_path):
    append_hook_message(
        tmp_path,
        "Stop",
        json.dumps({"session_id": "new-session", "last_assistant_message": "Ответ."}),
    )
    row = json.loads((tmp_path / "messages.jsonl").read_text())
    assert row["turn_index"] is None
    assert row["turn_status"] == "unmatched_response"
