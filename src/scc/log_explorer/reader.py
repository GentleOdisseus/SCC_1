"""Read-only, allowlisted access to local Speedometer run files."""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RUN_FILES = (
    "config.json",
    "status.json",
    "speedometer.pid.json",
    "events.jsonl",
    "messages.jsonl",
    "context_samples.jsonl",
    "snapshots.jsonl",
)
JSONL_SOURCES = ("events", "messages", "context_samples", "snapshots")
_SOURCE_RANK = {name: index for index, name in enumerate(JSONL_SOURCES)}


@dataclass(frozen=True)
class Record:
    run_id: str
    source: str
    file: str
    line: int
    ts: float | None
    record_type: str
    fields: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    searchable: str = ""
    redactions: int = 0
    truncated: bool = False
    text_unavailable: bool = False
    issue: str | None = None

    @property
    def identity(self) -> tuple[str, str, str, int]:
        return (self.run_id, self.source, self.file, self.line)


@dataclass(frozen=True)
class RunInfo:
    run_id: str
    path: Path
    config: dict[str, Any]
    observer_state: str
    observer_updated_at: float | None
    observer_pid: int | None
    observer_started_at: float | None
    observer_error_present: bool
    task_lifecycle: str
    latest_snapshot: dict[str, Any] | None
    last_activity: float | None
    records: tuple[Record, ...]
    issues: tuple[str, ...]

    @property
    def progress(self) -> float | None:
        value = self.latest_snapshot.get("progress") if self.latest_snapshot else None
        return value if _number(value) else None

    @property
    def goal_reached(self) -> bool | None:
        value = self.latest_snapshot.get("goal_reached") if self.latest_snapshot else None
        return value if isinstance(value, bool) else None


def discover_runs(runs_root: Path | str) -> list[RunInfo]:
    """Load immediate, non-symlink run directories; never traverse workspaces."""
    root = Path(runs_root).expanduser().resolve()
    try:
        children = list(root.iterdir())
    except FileNotFoundError:
        return []
    except OSError:
        return []

    runs: list[RunInfo] = []
    for child in children:
        try:
            if child.is_symlink() or not child.is_dir():
                continue
            if not _inside(root, child):
                continue
            runs.append(load_run(child))
        except OSError:
            # A disappearing or unreadable run should not hide other runs.
            continue
    return sorted(
        runs,
        key=lambda run: (
            run.last_activity is None,
            -(run.last_activity or 0.0),
            run.run_id,
        ),
    )


def load_run(run_path: Path | str) -> RunInfo:
    path = Path(run_path)
    root = path.parent.resolve()
    if path.is_symlink() or not path.is_dir() or not _inside(root, path):
        raise OSError("run directory is not a safe direct directory")
    run_id = path.name
    issues: list[str] = []
    config, config_issue = _read_object(path, "config.json")
    status, status_issue = _read_object(path, "status.json")
    pid, pid_issue = _read_object(path, "speedometer.pid.json")
    for issue in (config_issue, status_issue, pid_issue):
        if issue:
            issues.append(issue)

    records: list[Record] = []
    for source in JSONL_SOURCES:
        file_name = f"{source}.jsonl"
        file_path = path / file_name
        if not _safe_file(path, file_path):
            issues.append(f"{file_name}: unavailable or unsafe")
            continue
        try:
            has_records = False
            with _open_nofollow_bytes(file_path) as stream:
                for line_no, raw_bytes in enumerate(stream, 1):
                    if not raw_bytes.strip():
                        continue
                    has_records = True
                    try:
                        raw = raw_bytes.decode("utf-8")
                        value = json.loads(raw)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        record = _problem_record(run_id, source, file_name, line_no, "parse error")
                    else:
                        record = _normalize_record(run_id, source, file_name, line_no, value)
                    records.append(record)
            if not has_records:
                issues.append(f"{file_name}: empty")
        except FileNotFoundError:
            issues.append(f"{file_name}: missing")
        except (OSError, UnicodeError):
            issues.append(f"{file_name}: unreadable")

    for issue in issues:
        file_name, _, description = issue.partition(": ")
        source = Path(file_name).stem
        records.append(Record(run_id, source, file_name, 0, None, "source_issue", {}, description, issue=description))

    records.sort(key=_record_sort_key)
    snapshot_records = [record for record in records if record.source == "snapshots" and record.issue is None]
    latest_snapshot_record = max(
        snapshot_records,
        key=lambda record: (record.ts is not None, record.ts if record.ts is not None else 0.0, record.line),
        default=None,
    )
    latest_snapshot = latest_snapshot_record.fields if latest_snapshot_record else None
    timestamps = [record.ts for record in records if record.ts is not None]
    status_time = _timestamp(status.get("updated_at"))
    if status_time is not None:
        timestamps.append(status_time)
    task_lifecycle = _task_lifecycle(records)

    return RunInfo(
        run_id=str(config.get("run_id")) if isinstance(config.get("run_id"), str) else run_id,
        path=path,
        config=_allow_config(config),
        observer_state=_observer_state(status, pid),
        observer_updated_at=_timestamp(status.get("updated_at")),
        observer_pid=_positive_int(pid.get("pid")),
        observer_started_at=_timestamp(pid.get("started_at")),
        observer_error_present=bool(status.get("error")),
        task_lifecycle=task_lifecycle,
        latest_snapshot=latest_snapshot,
        last_activity=max(timestamps) if timestamps else None,
        records=tuple(records),
        issues=tuple(issues),
    )


def _read_object(run_path: Path, file_name: str) -> tuple[dict[str, Any], str | None]:
    file_path = run_path / file_name
    if not _safe_file(run_path, file_path):
        return {}, f"{file_name}: unavailable or unsafe"
    try:
        with _open_nofollow(file_path) as stream:
            value = json.load(stream)
    except FileNotFoundError:
        return {}, f"{file_name}: missing"
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}, f"{file_name}: parse error"
    if not isinstance(value, dict):
        return {}, f"{file_name}: unsupported record"
    return value, None


def _normalize_record(run_id: str, source: str, file_name: str, line: int, value: Any) -> Record:
    if not isinstance(value, dict):
        return _problem_record(run_id, source, file_name, line, "unsupported record")
    ts = _timestamp(value.get("ts"))
    if source == "events":
        if not isinstance(value.get("kind"), str):
            return _problem_record(run_id, source, file_name, line, "unsupported record")
        fields: dict[str, Any] = {"kind": _short(value.get("kind"), 80)}
        node_id = _short(value.get("node_id"), 128)
        if node_id:
            fields["node_id"] = node_id
        payload = value.get("payload") if isinstance(value.get("payload"), dict) else {}
        for key, limit in (("event_name", 80), ("session_id", 128), ("tool_name", 80), ("outcome", 40)):
            item = _short(payload.get(key), limit)
            if item:
                fields[key] = item
        # Historical event dataclasses default these counters to zero. Don't
        # present that default as a measured zero; non-zero values are explicit.
        for key in ("tokens", "cost_usd", "duration_s"):
            item = value.get(key)
            if _number(item) and item != 0:
                fields[key] = item
        summary = " · ".join(fields[key] for key in ("event_name", "tool_name", "outcome") if fields.get(key)) or fields["kind"]
        return Record(run_id, source, file_name, line, ts, fields["kind"], fields, summary, summary)

    if source == "messages":
        role = value.get("role")
        expected_event = "UserPromptSubmit" if role == "user" else "Stop" if role == "assistant" else None
        if value.get("kind") != "conversation_message" or value.get("event_name") != expected_event:
            return _problem_record(run_id, source, file_name, line, "unsupported record")
        fields = {"role": role}
        for key, limit in (("event_name", 80), ("session_id", 128), ("prompt_id", 128), ("turn_status", 80)):
            item = _short(value.get(key), limit)
            if item:
                fields[key] = item
        for key in ("turn_index", "redactions"):
            item = value.get(key)
            if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
                fields[key] = item
        prompt_quality = _prompt_quality(value.get("prompt_completeness"))
        if prompt_quality:
            fields["prompt_completeness"] = prompt_quality
        text_value = value.get("text")
        text = text_value if isinstance(text_value, str) and value.get("text_status") == "ok" else ""
        truncated = value.get("truncated") is True
        redactions = fields.get("redactions", 0)
        summary = f"{'User prompt' if role == 'user' else 'Final response'}"
        if fields.get("turn_index") is not None:
            summary += f" · turn {fields['turn_index']}"
        return Record(run_id, source, file_name, line, ts, role, fields, summary, text, redactions, truncated, not bool(text))

    if source == "context_samples":
        if value.get("kind") != "context_sample":
            return _problem_record(run_id, source, file_name, line, "unsupported record")
        fields = {"source": "claude_code_statusline"}
        for key, limit in (("session_id", 128), ("prompt_id", 128)):
            item = _short(value.get(key), limit)
            if item:
                fields[key] = item
        for key in ("total_input_tokens", "total_output_tokens", "context_window_size", "used_percentage", "remaining_percentage"):
            item = value.get(key)
            if _number(item):
                fields[key] = item
        fields["current_usage"] = _usage(value.get("current_usage"))
        return Record(run_id, source, file_name, line, ts, "context_sample", fields, "Context sample")

    if source == "snapshots":
        if "progress" not in value and "goal_reached" not in value and "requirements" not in value:
            return _problem_record(run_id, source, file_name, line, "unsupported record")
        fields = {}
        for key in ("progress", "completion_distance", "progress_per_second", "q_min"):
            item = value.get(key)
            if _number(item):
                fields[key] = item
        if isinstance(value.get("goal_reached"), bool):
            fields["goal_reached"] = value["goal_reached"]
        if isinstance(value.get("run_id"), str):
            fields["run_id"] = _short(value["run_id"], 128)
        fields["requirements"] = _requirements(value.get("requirements"))
        progress = fields.get("progress")
        summary = f"Verified {progress:.0%}" if isinstance(progress, (int, float)) else "Verifier snapshot"
        return Record(run_id, source, file_name, line, ts, "snapshot", fields, summary)

    return _problem_record(run_id, source, file_name, line, "unsupported record")


def _task_lifecycle(records: list[Record]) -> str:
    """Show running only while a recorded session is explicitly open."""
    active: set[str] = set()
    observed_start = False
    for record in sorted(records, key=_record_sort_key):
        if record.source != "events" or record.issue:
            continue
        name = record.fields.get("event_name")
        session = record.fields.get("session_id")
        if name == "SessionStart" and session:
            active.add(session)
            observed_start = True
        elif name == "SessionEnd" and session:
            active.discard(session)
    return "running" if observed_start and active else "unknown"


def _observer_state(status: dict[str, Any], pid: dict[str, Any]) -> str:
    state = status.get("state")
    if state == "error":
        return "error"
    if state == "running":
        return "running" if isinstance(pid.get("pid"), int) and pid.get("pid") > 0 else "stale"
    if state == "stopped":
        return "stopped"
    if isinstance(pid.get("pid"), int) and pid.get("pid") > 0:
        return "stale"
    return "stale"


def _allow_config(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("run_id", "task_dir", "workspace", "project_root"):
        item = _short(value.get(key), 512)
        if item:
            result[key] = item
    started = _timestamp(value.get("started_at"))
    if started is not None:
        result["started_at"] = started
    return result


def _requirements(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {}
        requirement_id = _short(item.get("id"), 128)
        if requirement_id:
            row["id"] = requirement_id
        for key in ("q", "weight"):
            if _number(item.get(key)):
                row[key] = item[key]
        if isinstance(item.get("hard"), bool):
            row["hard"] = item["hard"]
        status = _short(item.get("status"), 80)
        if status:
            row["status"] = status
        result.append(row)
    return result


def _prompt_quality(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    score = value.get("score")
    criteria = value.get("criteria")
    if not _number(score) or not isinstance(criteria, dict):
        return None
    allowed = {key: bool(criteria[key]) for key in ("goal", "constraints", "deliverable", "acceptance") if isinstance(criteria.get(key), bool)}
    return {"score": score, "criteria": allowed}


def _usage(value: Any) -> dict[str, int | float | None] | None:
    if not isinstance(value, dict):
        return None
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return {key: value[key] if _number(value.get(key)) else None for key in keys}


def _problem_record(run_id: str, source: str, file_name: str, line: int, issue: str) -> Record:
    return Record(run_id, source, file_name, line, None, issue.replace(" ", "_"), {}, issue, issue=issue)


def _record_sort_key(record: Record) -> tuple[Any, ...]:
    return (record.ts is None, record.ts if record.ts is not None else 0.0, _SOURCE_RANK.get(record.source, 99), record.line, record.file)


def _safe_file(root: Path, path: Path) -> bool:
    try:
        if path.is_symlink():
            return False
        if not path.exists():
            return True
        if not path.is_file():
            return False
        return _inside(root.resolve(), path)
    except OSError:
        return False


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def _open_nofollow(path: Path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    return os.fdopen(fd, "r", encoding="utf-8")


def _open_nofollow_bytes(path: Path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    return os.fdopen(fd, "rb")


def _timestamp(value: Any) -> float | None:
    if not _number(value):
        return None
    return float(value)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _short(value: Any, limit: int) -> str | None:
    if isinstance(value, str) and value:
        return value[:limit]
    return None
