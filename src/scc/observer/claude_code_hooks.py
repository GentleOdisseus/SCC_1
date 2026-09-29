"""Ingest metadata and visible conversation text from Claude Code hooks."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from scc.config import load_config
from scc.observer.events import EventKind, TelemetryEvent

TRUNCATION_MARKER = "\n...[truncated]..."
SUPPORTED_EVENTS = {
    "SessionStart", "UserPromptSubmit", "PostToolUse", "PostToolUseFailure",
    "Stop", "PreCompact", "PostCompact", "SessionEnd",
}

_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk-ant-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}={0,2}"),
    re.compile(r"(?i)(\b(?:api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*[\"']?)([^\s\"',;]{8,})"),
)


def parse_hook_payload(event_name: str, raw: str) -> dict[str, Any]:
    if event_name not in SUPPORTED_EVENTS:
        raise ValueError(f"unsupported hook event: {event_name}")
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("hook input is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("hook input must be a JSON object")
    return data


def normalize_hook_payload(event_name: str, raw: str) -> TelemetryEvent:
    """Convert hook stdin JSON into a minimal metadata event."""
    data = parse_hook_payload(event_name, raw)
    session_id = _short_string(data.get("session_id") or data.get("sessionId"), 128)
    tool_name = _short_string(data.get("tool_name") or data.get("toolName"), 80)
    outcome = {
        "PostToolUse": "success",
        "PostToolUseFailure": "failure",
    }.get(event_name)

    payload: dict[str, Any] = {"event_name": event_name}
    if session_id:
        payload["session_id"] = session_id
    if tool_name:
        payload["tool_name"] = tool_name
    if outcome:
        payload["outcome"] = outcome

    return TelemetryEvent(
        kind=EventKind.SESSION_EVENT,
        node_id="session",
        payload=payload,
        ts=time.time(),
    )


def append_hook_event(run_dir: str | Path, event_name: str, raw: str) -> TelemetryEvent:
    """Append one normalized metadata event using a single O_APPEND write."""
    run_path = Path(run_dir)
    event = normalize_hook_payload(event_name, raw)
    event.node_id = run_path.name
    _append_jsonl(run_path / "events.jsonl", event.to_dict())
    return event


def append_hook_message(run_dir: str | Path, event_name: str, raw: str) -> dict[str, Any] | None:
    """Append visible user prompts and final assistant responses only."""
    if event_name not in {"UserPromptSubmit", "Stop"}:
        return None
    data = parse_hook_payload(event_name, raw)
    session_id = _short_string(data.get("session_id") or data.get("sessionId"), 128)
    prompt_id = _short_string(data.get("prompt_id") or data.get("promptId"), 128)
    if event_name == "UserPromptSubmit":
        role, text_value = "user", data.get("prompt")
    else:
        role, text_value = "assistant", data.get("last_assistant_message")

    run_path = Path(run_dir)
    turn_index, turn_status = _turn_index(run_path / "messages.jsonl", event_name, session_id, prompt_id)
    if isinstance(text_value, str):
        text, redactions, truncated = _clean_message(text_value)
        text_status = "ok"
    else:
        text, redactions, truncated = None, 0, False
        text_status = "unavailable"

    record: dict[str, Any] = {
        "kind": "conversation_message",
        "role": role,
        "event_name": event_name,
        "session_id": session_id,
        "prompt_id": prompt_id,
        "turn_index": turn_index,
        "turn_status": turn_status,
        "ts": time.time(),
        "text": text,
        "text_status": text_status,
        "truncated": truncated,
        "redactions": redactions,
    }
    if role == "user" and text is not None:
        from scc.geometry.prompt_quality import assess_prompt

        record["prompt_completeness"] = assess_prompt(text)
    _append_jsonl(run_path / "messages.jsonl", record)
    return record


def _turn_index(path: Path, event_name: str, session_id: str | None, prompt_id: str | None) -> tuple[int | None, str]:
    if not session_id:
        return None, "unmatched_no_session_id"
    records = _read_messages(path)
    if prompt_id:
        if event_name == "UserPromptSubmit":
            return _next_index(records, session_id), "matched_by_prompt_id"
        matching = [
            int(item["turn_index"])
            for item in records
            if item.get("session_id") == session_id and item.get("prompt_id") == prompt_id and item.get("role") == "user"
        ]
        return (matching[-1], "matched_by_prompt_id") if matching else (None, "unmatched_prompt_id")

    if event_name == "UserPromptSubmit":
        return _next_index(records, session_id), "ordered_by_session"
    completed = {
        item.get("turn_index")
        for item in records
        if item.get("session_id") == session_id and item.get("role") == "assistant"
    }
    pending = [
        int(item["turn_index"])
        for item in records
        if item.get("session_id") == session_id and item.get("role") == "user" and item.get("turn_index") not in completed
    ]
    return (pending[-1], "ordered_by_session") if pending else (None, "unmatched_response")


def _next_index(records: list[dict[str, Any]], session_id: str) -> int:
    indexes = [
        int(item["turn_index"])
        for item in records
        if item.get("session_id") == session_id and item.get("role") == "user" and isinstance(item.get("turn_index"), int)
    ]
    return max(indexes, default=0) + 1


def _read_messages(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _clean_message(text: str) -> tuple[str, int, bool]:
    redactions = 0
    for pattern in _SECRET_PATTERNS:
        if pattern.groups == 2:
            text, count = pattern.subn(lambda match: match.group(1) + "[REDACTED]", text)
        else:
            text, count = pattern.subn("[REDACTED]", text)
        redactions += count

    configured_limit = int(load_config().get("speedometer", {}).get("message_max_bytes", 65536))
    max_bytes = max(1024, configured_limit)
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, redactions, False
    marker_text = f"\n...[truncated at {max_bytes} bytes]..."
    marker = marker_text.encode("utf-8")
    prefix = encoded[:max_bytes - len(marker)].decode("utf-8", errors="ignore")
    return prefix + marker_text, redactions, True


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        written = os.write(fd, line)
        if written != len(line):
            raise OSError("short write while appending hook data")
    finally:
        os.close(fd)


def _short_string(value: Any, limit: int) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[:limit]
