"""Local, verifier-backed speedometer for a Claude Code task run."""
from __future__ import annotations

import argparse
import json
from collections import deque
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any

import yaml

from scc.config import load_config
from scc.geometry.distance import goal_reached, progress
from scc.models import Goal, Requirement
from scc.observer.claude_code_hooks import append_hook_event, append_hook_message
from scc.observer.events import EventKind
from scc.observer.statusline import append_statusline_sample

RUNS_DIR = Path("experiments/runs")
HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PostToolUse",
    "PostToolUseFailure",
    "Stop",
    "PreCompact",
    "PostCompact",
    "SessionEnd",
)
HOOK_MARKER = "scc-speedometer-managed"


def _run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value) or value in {".", ".."}:
        raise ValueError("run id must contain only letters, digits, '.', '_' or '-' and start with a letter or digit")
    return value


def _json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _jsonl_append(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        if os.write(fd, line) != len(line):
            raise OSError("short JSONL write")
    finally:
        os.close(fd)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return data


def _read_last_jsonl(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    last: dict[str, Any] | None = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    last = value
    return last


def _recent_jsonl(path: Path, limit: int = 8) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: deque[dict[str, Any]] = deque(maxlen=limit)
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return list(rows)


def _latest_prompt_quality(run_dir: Path) -> dict[str, Any] | None:
    rows = _recent_jsonl(run_dir / "messages.jsonl", limit=200)
    for item in reversed(rows):
        if item.get("role") == "user" and isinstance(item.get("prompt_completeness"), dict):
            result = dict(item["prompt_completeness"])
            result["ts"] = item.get("ts")
            result["turn_index"] = item.get("turn_index")
            return result
    return None


def _latest_context_usage(run_dir: Path, now: float) -> dict[str, Any] | None:
    sample = _read_last_jsonl(run_dir / "context_samples.jsonl")
    if not sample:
        return None
    settings = load_config().get("speedometer", {})
    stale_after = float(settings.get("context_sample_stale_seconds", 60))
    age = max(0.0, now - float(sample.get("ts", now)))
    result = {key: sample.get(key) for key in (
        "ts", "session_id", "total_input_tokens", "total_output_tokens",
        "context_window_size", "used_percentage", "remaining_percentage", "current_usage",
    )}
    result["age_seconds"] = age
    result["stale"] = age > stale_after
    return result


def _load_goal(task_dir: Path) -> Goal:
    goal_path = task_dir / "goal.yaml"
    with goal_path.open(encoding="utf-8") as stream:
        spec = yaml.safe_load(stream) or {}
    requirements = []
    for item in spec.get("requirements", []):
        requirements.append(
            Requirement(
                id=str(item["id"]),
                weight=float(item["weight"]),
                q=0.0,
                hard=bool(item.get("hard", False)),
                source="verifier",
            )
        )
    if not requirements:
        raise ValueError(f"no requirements declared in {goal_path}")
    if len({item.id for item in requirements}) != len(requirements):
        raise ValueError(f"requirement ids must be unique in {goal_path}")
    if any(item.weight <= 0 for item in requirements):
        raise ValueError(f"requirement weights must be positive in {goal_path}")
    q_min = float(spec.get("q_min", 1.0))
    if not 0.0 <= q_min <= 1.0:
        raise ValueError(f"q_min must be between 0 and 1 in {goal_path}")
    return Goal(requirements=requirements, q_min=q_min)


def _check_verifier(task_dir: Path, workspace: Path, verifier: str) -> tuple[float, str]:
    rel = Path(verifier)
    if rel.is_absolute() or ".." in rel.parts:
        return 0.0, "invalid verifier path"
    script = (task_dir / rel).resolve()
    if not script.is_relative_to(task_dir.resolve()) or not script.is_file():
        return 0.0, "verifier missing or outside task directory"
    if script.suffix == ".sh":
        argv = ["/bin/sh", str(script)]
    elif script.suffix == ".py":
        argv = [sys.executable, str(script)]
    else:
        return 0.0, "verifier must be a .sh or .py script"
    env = os.environ.copy()
    env["SCC_WORKSPACE"] = str(workspace)
    try:
        result = subprocess.run(
            argv,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 0.0, f"verifier error: {type(exc).__name__}"
    match = re.search(r"(?:^|\s)q\s*=\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*$", result.stdout.strip())
    if result.returncode != 0:
        return 0.0, f"failed (exit {result.returncode})"
    if not match:
        return 0.0, "invalid verifier output; expected q=<0..1>"
    return min(1.0, max(0.0, float(match.group(1)))), "ok"


def collect_snapshot(run_dir: Path) -> dict[str, Any]:
    config = _read_json(run_dir / "config.json")
    task_dir = Path(config["task_dir"])
    workspace = Path(config["workspace"])
    goal_spec = yaml.safe_load((task_dir / "goal.yaml").read_text(encoding="utf-8")) or {}
    goal = _load_goal(task_dir)
    requirement_results = []
    for requirement, spec in zip(goal.requirements, goal_spec["requirements"]):
        q, detail = _check_verifier(task_dir, workspace, str(spec["verifier"]))
        requirement.q = q
        requirement_results.append({"id": requirement.id, "q": q, "weight": requirement.weight, "hard": requirement.hard, "status": detail})

    event_count = 0
    event_counts: dict[str, int] = {}
    events_path = run_dir / "events.jsonl"
    if events_path.exists():
        with events_path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("kind") == EventKind.SESSION_EVENT.value:
                    event_count += 1
                    name = str(event.get("payload", {}).get("event_name", "unknown"))
                    event_counts[name] = event_counts.get(name, 0) + 1

    now = time.time()
    previous = _read_last_jsonl(run_dir / "snapshots.jsonl")
    q = progress(goal)
    context_usage = _latest_context_usage(run_dir, now)
    prompt_completeness = _latest_prompt_quality(run_dir)
    elapsed = max(0.001, now - float(previous["ts"])) if previous else None
    speed = (q - float(previous["progress"])) / elapsed if previous and elapsed else None
    snapshot = {
        "ts": now,
        "run_id": config["run_id"],
        "progress": q,
        "completion_distance": 1.0 - q,
        "progress_per_second": speed,
        "goal_reached": goal_reached(goal),
        "q_min": goal.q_min,
        "requirements": requirement_results,
        "session_event_count": event_count,
        "session_events_by_type": event_counts,
        "latest_prompt_completeness": prompt_completeness,
        "context_usage": context_usage,
        "uncertainty": None,
    }
    _jsonl_append(run_dir / "snapshots.jsonl", snapshot)
    return snapshot


def _worker(run_dir: Path, interval: float) -> int:
    stopping = False

    def request_stop(_signum: int, _frame: Any) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    pid_path = run_dir / "speedometer.pid.json"
    _json_write(pid_path, {"pid": os.getpid(), "started_at": time.time()})
    try:
        while not stopping:
            try:
                collect_snapshot(run_dir)
                _json_write(run_dir / "status.json", {"state": "running", "updated_at": time.time()})
            except Exception as exc:
                _json_write(run_dir / "status.json", {"state": "error", "error": f"{type(exc).__name__}: {exc}", "updated_at": time.time()})
            deadline = time.monotonic() + max(1.0, interval)
            while not stopping and time.monotonic() < deadline:
                time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))
    finally:
        try:
            status = _read_json(run_dir / "status.json")
        except (OSError, ValueError, json.JSONDecodeError):
            status = {}
        status.update({"state": "stopped", "updated_at": time.time()})
        _json_write(run_dir / "status.json", status)
        try:
            pid_data = _read_json(pid_path)
            if pid_data.get("pid") == os.getpid():
                pid_path.unlink(missing_ok=True)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return 0


def _pid_state(run_dir: Path) -> tuple[str, int | None]:
    pid_path = run_dir / "speedometer.pid.json"
    if not pid_path.exists():
        state = _read_last_jsonl(run_dir / "snapshots.jsonl")
        return ("stopped", None) if state else ("not-started", None)
    try:
        pid = int(_read_json(pid_path)["pid"])
        os.kill(pid, 0)
        return "running", pid
    except ProcessLookupError:
        return "stale", None
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return "stale", None


def _run_dir(run_id: str) -> Path:
    return RUNS_DIR / _run_id(run_id)


def _prepare(args: argparse.Namespace) -> int:
    run_id = _run_id(args.run_id)
    run_dir = _run_dir(run_id)
    task_dir = Path(args.task_dir).resolve()
    workspace = Path(args.workspace).resolve() if args.workspace else (run_dir / "workspace").resolve()
    context_source = task_dir / "context" / "CLAUDE.md"
    if not context_source.is_file():
        raise ValueError(f"task context not found: {context_source}")
    if (run_dir / "config.json").exists():
        raise ValueError(f"run id {run_id} already exists; choose a new run id")
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError(f"workspace is not empty: {workspace}")

    (workspace / "demos" / "snake" / "context").mkdir(parents=True, exist_ok=True)
    (workspace / "demos" / "snake" / "rules").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(context_source, workspace / "demos" / "snake" / "context" / "CLAUDE.md")
    (workspace / "CLAUDE.md").write_text(
        "# Snake measurement workspace\n\n"
        "@demos/snake/context/CLAUDE.md\n",
        encoding="utf-8",
    )
    (workspace / "demos" / "snake" / "README.md").write_text(
        "# Snake experiment\n\n"
        "This is a clean prompt-driven workspace. Implement the game here; leave the reference demo untouched.\n",
        encoding="utf-8",
    )
    print(f"Prepared clean workspace for {run_id}: {workspace}")
    print(f"Start Claude Code with this workspace as CWD so its CLAUDE.md loads.")
    return 0


def _start(args: argparse.Namespace) -> int:
    run_id = _run_id(args.run_id)
    run_dir = _run_dir(run_id)
    task_dir = Path(args.task_dir).resolve()
    workspace_arg = getattr(args, "workspace", None)
    prepared_workspace = run_dir / "workspace"
    workspace = Path(workspace_arg).resolve() if workspace_arg else (prepared_workspace.resolve() if prepared_workspace.is_dir() else Path.cwd().resolve())
    if not (task_dir / "goal.yaml").is_file():
        raise ValueError(f"task goal not found: {task_dir / 'goal.yaml'}")
    if not workspace.is_dir():
        raise ValueError(f"workspace not found: {workspace}")
    state, _ = _pid_state(run_dir) if run_dir.exists() else ("not-started", None)
    if state == "running":
        raise ValueError(f"speedometer is already running for {run_id}")
    if (run_dir / "config.json").exists():
        raise ValueError(f"run id {run_id} already has data; choose a new run id")
    if RUNS_DIR.exists():
        for existing in RUNS_DIR.iterdir():
            if existing.is_dir() and existing.resolve() != run_dir.resolve() and _pid_state(existing)[0] == "running":
                raise ValueError(f"another speedometer run is active: {existing.name}")
    run_dir.mkdir(parents=True, exist_ok=True)
    speedometer_cfg = load_config().get("speedometer", {})
    _json_write(run_dir / "config.json", {
        "run_id": run_id,
        "task_dir": str(task_dir),
        "workspace": str(workspace),
        "project_root": str(Path.cwd().resolve()),
        "context_sample_stale_seconds": float(speedometer_cfg.get("context_sample_stale_seconds", 60)),
        "started_at": time.time(),
    })
    if args.background:
        log_path = run_dir / "speedometer.log"
        child_env = os.environ.copy()
        source_root = str(Path(__file__).resolve().parents[2])
        child_env["PYTHONPATH"] = os.pathsep.join(filter(None, (source_root, child_env.get("PYTHONPATH", ""))))
        with log_path.open("a", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "scc.observer.speedometer", "_worker", "--run-dir", str(run_dir.resolve()), "--interval", str(args.interval)],
                cwd=Path.cwd(),
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
        _json_write(run_dir / "speedometer.pid.json", {"pid": process.pid, "started_at": time.time()})
        print(f"Speedometer started in background: pid={process.pid} run={run_id}")
        print(f"Logs: {log_path}")
        return 0
    return _worker(run_dir.resolve(), args.interval)


def _status(run_id: str) -> int:
    run_dir = _run_dir(run_id)
    state, pid = _pid_state(run_dir)
    print(f"run: {run_id}\nstate: {state}")
    if pid:
        print(f"pid: {pid}")
    snapshot = _read_last_jsonl(run_dir / "snapshots.jsonl")
    if snapshot:
        print(f"verified progress: {snapshot['progress']:.1%}")
        print(f"goal reached: {'yes' if snapshot['goal_reached'] else 'no'}")
        print(f"session events: {snapshot['session_event_count']}")
        context = snapshot.get("context_usage")
        if not context:
            print("context usage: unavailable")
        elif context.get("stale"):
            print(f"context usage: stale sample ({context['age_seconds']:.0f}s old)")
        else:
            pct = context.get("used_percentage")
            used = context.get("total_input_tokens")
            size = context.get("context_window_size")
            print(f"context usage: {pct:.0f}% · {used:,}/{size:,} input tokens" if pct is not None and used is not None and size else "context usage: unavailable")
        prompt_score = snapshot.get("latest_prompt_completeness")
        if prompt_score:
            print(f"latest prompt completeness: {prompt_score['score']:.0%}")
        print(f"recent message records: {len(_recent_jsonl(run_dir / 'messages.jsonl', limit=100))}")
    status_path = run_dir / "status.json"
    if status_path.exists():
        status = _read_json(status_path)
        if status.get("state") == "error":
            print(f"last error: {status.get('error', 'unknown')}")
    return 0


def _stop(run_id: str) -> int:
    run_dir = _run_dir(run_id)
    state, pid = _pid_state(run_dir)
    if state != "running" or pid is None:
        print(f"speedometer is not running (state={state})")
        return 1 if state == "stale" else 0
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current, _ = _pid_state(run_dir)
        if current != "running":
            break
        time.sleep(0.1)
    current, _ = _pid_state(run_dir)
    if current == "running":
        print(f"stop requested for pid={pid}; process has not exited yet")
        return 1
    print(f"stopped run {run_id}")
    return 0


def _run_config(run_id: str) -> tuple[Path, dict[str, Any]]:
    run_dir = _run_dir(run_id).resolve()
    if not (run_dir / "config.json").is_file():
        raise ValueError(f"run not initialized: {run_id}; start it before installing integrations")
    return run_dir, _read_json(run_dir / "config.json")


def _workspace_settings_path(config: dict[str, Any]) -> Path:
    return Path(config["workspace"]) / ".claude" / "settings.local.json"


def _read_workspace_settings(path: Path) -> dict[str, Any]:
    return _read_json(path) if path.exists() else {}


def _hook_install(run_id: str) -> int:
    run_dir, config = _run_config(run_id)
    settings_path = _workspace_settings_path(config)
    settings = _read_workspace_settings(settings_path)
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings hooks field must be a JSON object")
    if _has_managed_hook(hooks):
        if any(_managed_run_id(entry) == run_id for entries in hooks.values() if isinstance(entries, list) for entry in entries):
            print(f"speedometer hooks already installed for {run_id}")
            return 0
        raise ValueError("another SCC speedometer hook set is installed; uninstall it before switching runs")
    for event_name in HOOK_EVENTS:
        command = shlex.join([sys.executable, "-m", "scc.observer.speedometer", "hook", "--run-dir", str(run_dir), "--event-name", event_name])
        hooks.setdefault(event_name, []).append({
            "hooks": [{"type": "command", "command": command, "timeout": 5, "statusMessage": f"{HOOK_MARKER}:{run_id}"}],
        })
    _json_write(settings_path, settings)
    print(f"Installed opt-in hooks in {settings_path}; prompt and final-response text will be stored locally.")
    print("Launch Claude Code with this workspace as CWD, then reload hooks or start a new session.")
    return 0


def _managed_run_id(entry: Any) -> str | None:
    if not isinstance(entry, dict):
        return None
    for hook in entry.get("hooks", []):
        if not isinstance(hook, dict):
            continue
        marker = str(hook.get("statusMessage", ""))
        if marker.startswith(f"{HOOK_MARKER}:"):
            return marker.partition(":")[2]
    return None


def _has_managed_hook(hooks: dict[str, Any]) -> bool:
    return any(
        _managed_run_id(entry) is not None
        for entries in hooks.values() if isinstance(entries, list)
        for entry in entries
    )


def _hook_uninstall(run_id: str) -> int:
    _, config = _run_config(run_id)
    settings_path = _workspace_settings_path(config)
    if not settings_path.exists():
        print("no workspace-local settings file; nothing to uninstall")
        return 0
    settings = _read_json(settings_path)
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings hooks field must be a JSON object")
    for event_name, entries in list(hooks.items()):
        if isinstance(entries, list):
            hooks[event_name] = [entry for entry in entries if _managed_run_id(entry) != run_id]
            if not hooks[event_name]:
                del hooks[event_name]
    if not hooks:
        settings.pop("hooks", None)
    _json_write(settings_path, settings)
    print(f"Removed SCC speedometer hooks for {run_id} from {settings_path}; unrelated settings were preserved.")
    return 0


def _managed_statusline_run_id(status_line: Any) -> str | None:
    if not isinstance(status_line, dict):
        return None
    command = str(status_line.get("command", ""))
    try:
        parts = shlex.split(command)
        run_dir = parts[parts.index("--run-dir") + 1]
    except (ValueError, IndexError):
        return None
    if "scc.observer.statusline" not in parts:
        return None
    return Path(run_dir).name or None


def _has_effective_statusline(workspace: Path, target: Path) -> bool:
    candidates = [Path.home() / ".claude" / "settings.json"]
    for parent in workspace.parents:
        candidates.extend((parent / ".claude" / "settings.json", parent / ".claude" / "settings.local.json"))
    candidates.extend((workspace / ".claude" / "settings.json", target))
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or resolved == target.resolve():
            continue
        seen.add(resolved)
        if candidate.is_file():
            settings = _read_json(candidate)
            if settings.get("statusLine"):
                return True
    return False


def _statusline_install(run_id: str) -> int:
    run_dir, config = _run_config(run_id)
    workspace = Path(config["workspace"])
    settings_path = _workspace_settings_path(config)
    settings = _read_workspace_settings(settings_path)
    status_line = settings.get("statusLine")
    if status_line:
        command = str(status_line.get("command", "")) if isinstance(status_line, dict) else ""
        if f"--run-dir {run_dir}" in command and "scc.observer.statusline" in command:
            print(f"StatusLine telemetry already installed for {run_id}")
            return 0
        raise ValueError(f"existing StatusLine in {settings_path}; refusing to replace it")
    if _has_effective_statusline(workspace, settings_path):
        raise ValueError("an inherited StatusLine already exists; refusing to override it")

    refresh = int(load_config().get("speedometer", {}).get("statusline_refresh_interval_seconds", 5))
    command = shlex.join([sys.executable, "-m", "scc.observer.statusline", "--run-dir", str(run_dir)])
    settings["statusLine"] = {"type": "command", "command": command, "refreshInterval": refresh}
    _json_write(settings_path, settings)
    print(f"Installed workspace-local context telemetry in {settings_path}.")
    return 0


def _statusline_uninstall(run_id: str) -> int:
    _, config = _run_config(run_id)
    settings_path = _workspace_settings_path(config)
    if not settings_path.exists():
        print("no workspace-local settings file; nothing to uninstall")
        return 0
    settings = _read_json(settings_path)
    if _managed_statusline_run_id(settings.get("statusLine")) != run_id:
        print("no SCC StatusLine integration for this run; unrelated settings were preserved")
        return 0
    settings.pop("statusLine", None)
    _json_write(settings_path, settings)
    print(f"Removed SCC StatusLine integration for {run_id} from {settings_path}.")
    return 0


def _event_feed(run_dir: Path, limit: int = 5) -> list[dict[str, Any]]:
    path = run_dir / "events.jsonl"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("kind") == EventKind.SESSION_EVENT.value:
                rows.append(item)
    return rows[-limit:]


def _messages_feed(run_dir: Path, limit: int = 4) -> list[dict[str, Any]]:
    return _recent_jsonl(run_dir / "messages.jsonl", limit=limit)


def _display_text(value: Any, width: int = 92) -> str:
    if not isinstance(value, str):
        return "[unavailable]"
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", text)
    return textwrap.shorten(" ".join(text.split()), width=width, placeholder=" …") or "[empty]"


def _render(run_id: str) -> str:
    run_dir = _run_dir(run_id)
    snapshot = _read_last_jsonl(run_dir / "snapshots.jsonl")
    status = {}
    status_path = run_dir / "status.json"
    if status_path.exists():
        try:
            status = _read_json(status_path)
        except (OSError, ValueError, json.JSONDecodeError):
            status = {"state": "error", "error": "status file is unreadable"}
    error_line = f"Observer error: {status.get('error', 'unknown')}" if status.get("state") == "error" else None
    if not snapshot:
        lines = [f"SCC SPEEDOMETER · {run_id}"]
        if error_line:
            lines.append(error_line)
        lines.append("Waiting for first verifier snapshot...")
        return "\n".join(lines)
    q = float(snapshot["progress"])
    target = float(snapshot["q_min"])
    width = 32
    position = min(width, round(q * width))
    bar = "━" * position + "●" + "─" * (width - position)
    requirements = snapshot.get("requirements", [])
    failed_hard = any(item["hard"] and item["q"] < 1.0 for item in requirements)
    if snapshot["goal_reached"]:
        color, label = "\033[32m", "GOAL VERIFIED"
    elif failed_hard:
        color, label = "\033[31m", "HARD CHECK FAILED"
    else:
        color, label = "\033[33m", "IN PROGRESS"
    reset = "\033[0m"
    lines = [
        f"SCC SPEEDOMETER · {run_id}",
        "─" * 56,
        f"{color}{label}{reset}   verified {q:.0%}   remaining {max(0.0, 1.0 - q):.0%}   target q_min {target:.0%}",
        f"Start  {bar}  Goal",
        "",
        "Criteria:",
    ]
    if error_line:
        lines.insert(2, error_line)
    for item in requirements:
        mark = "✓" if item["q"] >= 1.0 else ("!" if item["hard"] and item["q"] < 1 else "·")
        lines.append(f" {mark} {item['id']:<20} {item['q']:.0%}  {item['status']}")
    context = snapshot.get("context_usage")
    if not context:
        context_label = "unavailable (StatusLine sample not received)"
    elif context.get("stale"):
        context_label = f"stale ({context.get('age_seconds', 0):.0f}s old)"
    else:
        used = context.get("total_input_tokens")
        size = context.get("context_window_size")
        pct = context.get("used_percentage")
        if used is None or size is None or pct is None:
            context_label = "unavailable (field missing/null)"
        else:
            context_label = f"{pct:.0f}% · {used:,}/{size:,} input tokens"
    lines.extend(["", f"Context window: {context_label}"])

    prompt_quality = snapshot.get("latest_prompt_completeness")
    if prompt_quality:
        flags = prompt_quality.get("criteria", {})
        checklist = " ".join(f"{name}={'✓' if value else '·'}" for name, value in flags.items())
        lines.append(f"Latest prompt completeness heuristic: {prompt_quality['score']:.0%} · {checklist}")
    else:
        lines.append("Latest prompt completeness: unavailable")

    lines.extend(["", f"Session events: {snapshot['session_event_count']}", "Recent session events:"])
    for event in _event_feed(run_dir):
        payload = event.get("payload", {})
        stamp = time.strftime("%H:%M:%S", time.localtime(float(event.get("ts", 0))))
        tool = payload.get("tool_name") or ""
        outcome = payload.get("outcome") or ""
        lines.append(f" {stamp} {payload.get('event_name', 'event')} {tool} {outcome}".rstrip())

    lines.extend(["", "Recent prompt / final response feed:"])
    for message in _messages_feed(run_dir):
        stamp = time.strftime("%H:%M:%S", time.localtime(float(message.get("ts", 0))))
        role = "User" if message.get("role") == "user" else "Claude final"
        turn = message.get("turn_index")
        turn_text = f" turn {turn}" if turn is not None else ""
        lines.append(f" {stamp}{turn_text} {role}: {_display_text(message.get('text'))}")
        quality = message.get("prompt_completeness")
        if role == "User" and isinstance(quality, dict):
            flags = " ".join(f"{name}={'✓' if value else '·'}" for name, value in quality.get("criteria", {}).items())
            lines.append(f"   Q_prompt {quality['score']:.0%} · {flags}")
    return "\n".join(lines)


def _watch(run_id: str) -> int:
    if not sys.stdout.isatty():
        print(_render(run_id))
        return 0
    try:
        while True:
            sys.stdout.write("\033[2J\033[H" + _render(run_id) + "\n\nCtrl-C to detach from watch\n")
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDetached from speedometer watch.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scc-speedometer", description="Observe a task run from Claude Code hooks and verifiers")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="prepare a clean prompt-driven task workspace")
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--task-dir", default="experiments/tasks/snake")
    prepare.add_argument("--workspace")

    start = sub.add_parser("start", help="start the run observer")
    start.add_argument("--run-id", required=True)
    start.add_argument("--task-dir", default="experiments/tasks/snake")
    start.add_argument("--workspace")
    start.add_argument("--interval", type=float, default=10.0)
    start.add_argument("--background", action="store_true")

    status = sub.add_parser("status", help="show the latest run status")
    status.add_argument("--run-id", required=True)

    stop = sub.add_parser("stop", help="stop the background observer")
    stop.add_argument("--run-id", required=True)

    watch = sub.add_parser("watch", help="render the live terminal speedometer")
    watch.add_argument("--run-id", required=True)

    hooks = sub.add_parser("hooks", help="manage the opt-in Claude Code hook adapter")
    hook_sub = hooks.add_subparsers(dest="hook_command", required=True)
    install = hook_sub.add_parser("install", help="install metadata-only project-local hooks")
    install.add_argument("--run-id", required=True)
    uninstall = hook_sub.add_parser("uninstall", help="remove only SCC speedometer hooks")
    uninstall.add_argument("--run-id", required=True)

    statusline = sub.add_parser("statusline", help="manage context-window sampling")
    statusline_sub = statusline.add_subparsers(dest="statusline_command", required=True)
    statusline_install = statusline_sub.add_parser("install", help="install workspace-local context sampling")
    statusline_install.add_argument("--run-id", required=True)
    statusline_uninstall = statusline_sub.add_parser("uninstall", help="remove SCC context sampling")
    statusline_uninstall.add_argument("--run-id", required=True)

    hook = sub.add_parser("hook", help=argparse.SUPPRESS)
    hook.add_argument("--run-dir", required=True)
    hook.add_argument("--event-name", required=True)

    worker = sub.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("--run-dir", required=True)
    worker.add_argument("--interval", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            return _prepare(args)
        if args.command == "start":
            return _start(args)
        if args.command == "status":
            return _status(args.run_id)
        if args.command == "stop":
            return _stop(args.run_id)
        if args.command == "watch":
            return _watch(args.run_id)
        if args.command == "hooks" and args.hook_command == "install":
            return _hook_install(args.run_id)
        if args.command == "hooks" and args.hook_command == "uninstall":
            return _hook_uninstall(args.run_id)
        if args.command == "statusline" and args.statusline_command == "install":
            return _statusline_install(args.run_id)
        if args.command == "statusline" and args.statusline_command == "uninstall":
            return _statusline_uninstall(args.run_id)
        if args.command == "hook":
            raw = sys.stdin.read()
            append_hook_event(args.run_dir, args.event_name, raw)
            append_hook_message(args.run_dir, args.event_name, raw)
            return 0
        if args.command == "_worker":
            return _worker(Path(args.run_dir), args.interval)
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(f"scc-speedometer: {exc}", file=sys.stderr)
        return 2
    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
