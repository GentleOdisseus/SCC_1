"""Opt-in capture and rendering for the tracked SCC developer diary."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from scc.observer.claude_code_hooks import append_hook_message, parse_hook_payload  # noqa: E402

DIARY_ROOT = PROJECT_ROOT / "developer_diary"
HOOK_EVENTS = ("UserPromptSubmit", "Stop")
HOOK_MARKER = "scc-developer-diary-managed"
_RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain the local, review-before-commit SCC developer diary")
    sub = parser.add_subparsers(dest="command", required=True)

    hooks = sub.add_parser("hooks", help="install or remove local Claude Code diary hooks")
    hook_sub = hooks.add_subparsers(dest="hook_command", required=True)
    install = hook_sub.add_parser("install", help="opt in to local prompt/final-answer capture")
    install.add_argument("--workspace", type=Path, required=True)
    install.add_argument("--run-id", help="mark a Speedometer workspace scope")
    uninstall = hook_sub.add_parser("uninstall", help="remove only diary hooks from a workspace")
    uninstall.add_argument("--workspace", type=Path, required=True)
    uninstall.add_argument("--run-id", help="mark a Speedometer workspace scope")

    capture = sub.add_parser("capture", help="internal hook command; normally invoked automatically")
    capture.add_argument("--event-name", choices=HOOK_EVENTS, required=True)
    capture.add_argument("--scope", choices=("project", "speedometer"), required=True)
    capture.add_argument("--run-id")
    capture.add_argument("--diary-root", type=Path, default=DIARY_ROOT)

    sync = sub.add_parser("sync", help="render diary sessions and Git commit metadata")
    sync.add_argument("--diary-root", type=Path, default=DIARY_ROOT)
    sync.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    preview = sub.add_parser("preview", help="show generated-file counts without printing diary text")
    preview.add_argument("--diary-root", type=Path, default=DIARY_ROOT)
    preview.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "capture":
        try:
            return capture_message(args.event_name, args.scope, args.run_id, args.diary_root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            # A diary failure must never block the user's Claude Code turn.
            print(f"developer_diary capture failed: {type(exc).__name__}", file=sys.stderr)
            return 0
    try:
        if args.command == "hooks" and args.hook_command == "install":
            return install_hooks(args.workspace, args.run_id)
        if args.command == "hooks" and args.hook_command == "uninstall":
            return uninstall_hooks(args.workspace, args.run_id)
        if args.command == "sync":
            session_pages, commit_count = sync_diary(args.diary_root, args.project_root)
            print(f"Updated {session_pages} session page(s) and {commit_count} commit entry/entries.")
            print("Review `git diff developer_diary/` before committing; nothing was staged or pushed.")
            return 0
        if args.command == "preview":
            session_pages, commit_count = preview_sync(args.diary_root, args.project_root)
            print(f"Would update {session_pages} session page(s) and {commit_count} commit entry/entries.")
            print("No prompt or answer text is printed by preview.")
            return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"developer_diary: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 2


def install_hooks(workspace: Path | str, run_id: str | None = None) -> int:
    scope = _scope_name(run_id)
    workspace_path = Path(workspace).expanduser()
    if workspace_path.is_symlink():
        raise ValueError("workspace must not be a symlink")
    root = workspace_path.resolve()
    if not root.is_dir():
        raise ValueError("workspace must be an existing directory")
    settings_dir = root / ".claude"
    if settings_dir.is_symlink() or (settings_dir.exists() and not settings_dir.is_dir()):
        raise ValueError("workspace .claude path is unsafe")
    settings_path = settings_dir / "settings.local.json"
    if settings_path.is_symlink() or (settings_path.exists() and not settings_path.is_file()):
        raise ValueError("refusing to follow an unsafe settings path")

    settings = _read_settings(settings_path)
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings hooks field must be a JSON object")

    command_base = [
        sys.executable,
        str(Path(__file__).resolve()),
        "capture",
        "--diary-root",
        str(DIARY_ROOT.resolve()),
        "--scope",
        "speedometer" if run_id else "project",
    ]
    if run_id:
        command_base.extend(["--run-id", run_id])

    changed = False
    for event_name in HOOK_EVENTS:
        entries = hooks.setdefault(event_name, [])
        if not isinstance(entries, list):
            raise ValueError(f"settings hooks.{event_name} field must be a JSON array")
        marker = _marker(scope, event_name)
        if any(_contains_marker(entry, marker) for entry in entries):
            continue
        entries.append({
            "hooks": [{
                "type": "command",
                "command": shlex.join([*command_base, "--event-name", event_name]),
                "timeout": 10,
                "statusMessage": marker,
            }],
        })
        changed = True

    if changed:
        _write_settings(settings_path, settings)
        print(f"Installed local developer diary hooks in {settings_path}.")
    else:
        print(f"Developer diary hooks already installed in {settings_path}.")
    print("Only visible user prompts and final Stop responses are captured; commits remain manual.")
    return 0


def uninstall_hooks(workspace: Path | str, run_id: str | None = None) -> int:
    scope = _scope_name(run_id)
    workspace_path = Path(workspace).expanduser()
    if workspace_path.is_symlink():
        raise ValueError("workspace must not be a symlink")
    root = workspace_path.resolve()
    if not root.is_dir():
        raise ValueError("workspace must be an existing directory")
    settings_dir = root / ".claude"
    if settings_dir.is_symlink() or (settings_dir.exists() and not settings_dir.is_dir()):
        raise ValueError("workspace .claude path is unsafe")
    settings_path = settings_dir / "settings.local.json"
    if settings_path.is_symlink() or (settings_path.exists() and not settings_path.is_file()):
        raise ValueError("refusing to follow an unsafe settings path")
    if not settings_path.exists():
        print("No workspace-local settings file; nothing to uninstall.")
        return 0

    settings = _read_settings(settings_path)
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings hooks field must be a JSON object")

    changed = False
    for event_name in HOOK_EVENTS:
        entries = hooks.get(event_name)
        if not isinstance(entries, list):
            continue
        remaining, removed = _remove_marked_hooks(entries, _marker(scope, event_name))
        if removed:
            changed = True
            if remaining:
                hooks[event_name] = remaining
            else:
                hooks.pop(event_name, None)
    if changed:
        if not hooks:
            settings.pop("hooks", None)
        _write_settings(settings_path, settings)
        print(f"Removed developer diary hooks from {settings_path}; unrelated settings were preserved.")
    else:
        print("No diary hooks for this scope; unrelated settings were preserved.")
    return 0


def capture_message(event_name: str, scope: str, run_id: str | None, diary_root: Path | str) -> int:
    if event_name not in HOOK_EVENTS:
        return 0
    if scope not in {"project", "speedometer"}:
        raise ValueError("unsupported diary hook scope")
    scope_name = _scope_name(run_id) if scope == "speedometer" else "project"
    if (scope == "project" and run_id) or (scope == "speedometer" and not run_id):
        raise ValueError("speedometer scope requires --run-id; project scope does not accept one")

    raw = sys.stdin.read()
    data = parse_hook_payload(event_name, raw)
    capture_dir = _capture_directory(diary_root, scope_name, data.get("session_id") or data.get("sessionId"))
    _ensure_safe_capture_dir(diary_root, capture_dir)
    messages_path = capture_dir / "messages.jsonl"
    if messages_path.is_symlink() or (messages_path.exists() and not messages_path.is_file()):
        raise ValueError("unsafe diary message path")
    if _already_captured(messages_path, event_name, data):
        return 0

    record = append_hook_message(capture_dir, event_name, raw)
    if record is None:
        return 0
    render_session(diary_root, capture_dir)
    # Never print captured message text to hook stdout/stderr.
    return 0


def sync_diary(diary_root: Path | str, project_root: Path | str) -> tuple[int, int]:
    root = _validate_diary_root(diary_root)
    repo = Path(project_root).expanduser().resolve()
    session_pages = render_sessions(root)
    commits = _read_commits(repo)
    _write_diary_text_atomic(root, root / "commits.md", _render_commits(commits))
    return session_pages, len(commits)


def preview_sync(diary_root: Path | str, project_root: Path | str) -> tuple[int, int]:
    root = _validate_diary_root(diary_root)
    repo = Path(project_root).expanduser().resolve()
    scopes = {entry["source_scope"] for entry in _iter_entries(root)}
    commits = _read_commits(repo)
    return len(scopes), len(commits)


def _scope_name(run_id: str | None) -> str:
    if run_id is None:
        return "project"
    if not _RUN_ID_RE.fullmatch(run_id) or run_id in {".", ".."}:
        raise ValueError("run id must contain only letters, digits, '.', '_' or '-' and start with a letter or digit")
    return f"speedometer/{run_id}"


def _capture_directory(diary_root: Path | str, scope: str, session_id: Any) -> Path:
    root = _validate_diary_root(diary_root)
    session = session_id if isinstance(session_id, str) and session_id else "unmatched"
    session_key = hashlib.sha256(session.encode("utf-8")).hexdigest()[:16]
    scope_path = Path(scope)
    if scope_path.is_absolute() or any(part in {".", ".."} for part in scope_path.parts):
        raise ValueError("unsafe diary scope")
    return root / "captures" / scope_path / session_key


def _validate_diary_root(diary_root: Path | str) -> Path:
    raw = Path(diary_root).expanduser()
    if raw.is_symlink():
        raise ValueError("diary root must not be a symlink")
    root = raw.resolve()
    if root.exists() and not root.is_dir():
        raise ValueError("diary root must be a directory")
    return root


def _ensure_safe_directory(root: Path, directory: Path) -> None:
    root = _validate_diary_root(root)
    relative = directory.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("refusing to follow a symlink in the diary path")
        if current.exists() and not current.is_dir():
            raise ValueError("diary path component is not a directory")
        if not current.exists():
            current.mkdir(mode=0o700)


def _ensure_safe_capture_dir(diary_root: Path | str, capture_dir: Path) -> None:
    root = _validate_diary_root(diary_root)
    if not capture_dir.is_relative_to(root):
        raise ValueError("capture directory is outside the diary root")
    _ensure_safe_directory(root, capture_dir)


def _already_captured(path: Path, event_name: str, data: dict[str, Any]) -> bool:
    session_id = data.get("session_id") or data.get("sessionId")
    prompt_id = data.get("prompt_id") or data.get("promptId")
    if not isinstance(session_id, str) or not session_id or not isinstance(prompt_id, str) or not prompt_id:
        return False
    role = "user" if event_name == "UserPromptSubmit" else "assistant"
    if path.is_symlink():
        raise ValueError("refusing to follow a symlinked diary capture file")
    if not path.is_file():
        return False
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(record, dict)
                and record.get("event_name") == event_name
                and record.get("role") == role
                and record.get("session_id") == session_id
                and record.get("prompt_id") == prompt_id
            ):
                return True
    return False


def _marker(scope: str, event_name: str) -> str:
    return f"{HOOK_MARKER}:{scope}:{event_name}"


def _contains_marker(entry: Any, marker: str) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
        return False
    return any(isinstance(hook, dict) and hook.get("statusMessage") == marker for hook in entry["hooks"])


def _remove_marked_hooks(entries: list[Any], marker: str) -> tuple[list[Any], bool]:
    remaining: list[Any] = []
    removed = False
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
            remaining.append(entry)
            continue
        hooks = [hook for hook in entry["hooks"] if not (isinstance(hook, dict) and hook.get("statusMessage") == marker)]
        if len(hooks) == len(entry["hooks"]):
            remaining.append(entry)
        else:
            removed = True
            if hooks:
                updated = dict(entry)
                updated["hooks"] = hooks
                remaining.append(updated)
    return remaining, removed


def _read_settings(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("refusing to follow a symlinked settings file")
    if not path.exists():
        return {}
    if not path.is_file():
        raise ValueError("settings path must be a regular file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        settings = json.load(stream)
    if not isinstance(settings, dict):
        raise ValueError("settings file must contain a JSON object")
    return settings


def _write_settings(path: Path, settings: dict[str, Any]) -> None:
    _ensure_safe_directory(path.parent.parent, path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("refusing to replace an unsafe settings path")
    _write_diary_text_atomic(path.parent.parent, path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")


def _iter_capture_files(diary_root: Path) -> Iterator[tuple[str, Path]]:
    root = _validate_diary_root(diary_root)
    captures = root / "captures"
    if captures.is_symlink() or not captures.is_dir():
        return

    for scope_root_name in ("project", "speedometer"):
        scope_root = captures / scope_root_name
        if scope_root.is_symlink() or not scope_root.is_dir():
            continue
        if scope_root_name == "project":
            for session_dir in sorted(scope_root.iterdir()):
                yield from _capture_file(scope_root, session_dir, root, "project")
        else:
            for run_dir in sorted(scope_root.iterdir()):
                if run_dir.is_symlink() or not run_dir.is_dir():
                    continue
                for session_dir in sorted(run_dir.iterdir()):
                    yield from _capture_file(run_dir, session_dir, root, f"speedometer/{run_dir.name}")


def _capture_file(parent: Path, session_dir: Path, diary_root: Path, scope: str) -> Iterator[tuple[str, Path]]:
    if session_dir.is_symlink() or not session_dir.is_dir():
        return
    path = session_dir / "messages.jsonl"
    if path.is_symlink() or not path.is_file() or not _inside(diary_root, path):
        return
    yield f"{scope}/{session_dir.name}", path


def _iter_entries(diary_root: Path) -> Iterator[dict[str, Any]]:
    root = _validate_diary_root(diary_root)
    for scope, path in _iter_capture_files(root):
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    entry = _normalize_entry(raw, scope, line_number)
                    if entry is not None:
                        yield entry
        except (OSError, UnicodeError):
            continue


def _normalize_entry(raw: Any, scope: str, line_number: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or raw.get("kind") != "conversation_message":
        return None
    role = raw.get("role")
    event_name = raw.get("event_name")
    if role == "user" and event_name != "UserPromptSubmit":
        return None
    if role == "assistant" and event_name != "Stop":
        return None
    if role not in {"user", "assistant"}:
        return None
    text = raw.get("text") if raw.get("text_status") == "ok" and isinstance(raw.get("text"), str) else None
    stamp = raw.get("ts")
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
        stamp = None
    session_id = raw.get("session_id") if isinstance(raw.get("session_id"), str) else None
    prompt_id = raw.get("prompt_id") if isinstance(raw.get("prompt_id"), str) else None
    turn_index = raw.get("turn_index") if isinstance(raw.get("turn_index"), int) and not isinstance(raw.get("turn_index"), bool) else None
    redactions = raw.get("redactions") if isinstance(raw.get("redactions"), int) and not isinstance(raw.get("redactions"), bool) else 0
    truncated = raw.get("truncated") is True
    return {
        "source_scope": scope,
        "source_line": line_number,
        "event_name": event_name,
        "role": role,
        "session_id": session_id,
        "prompt_id": prompt_id,
        "turn_index": turn_index,
        "turn_status": raw.get("turn_status") if isinstance(raw.get("turn_status"), str) else None,
        "ts": float(stamp) if stamp is not None else None,
        "text": text,
        "text_status": raw.get("text_status") if isinstance(raw.get("text_status"), str) else "unavailable",
        "redactions": redactions,
        "truncated": truncated,
    }


def render_session(diary_root: Path | str, capture_dir: Path) -> None:
    root = _validate_diary_root(diary_root)
    captures_root = root / "captures"
    if capture_dir.is_symlink() or not capture_dir.is_dir():
        raise ValueError("capture directory is unavailable or unsafe")
    capture_dir = capture_dir.resolve()
    if not capture_dir.is_relative_to(captures_root.resolve()):
        raise ValueError("capture directory is outside diary captures")
    scope = capture_dir.relative_to(captures_root.resolve()).as_posix()
    messages_path = capture_dir / "messages.jsonl"
    if messages_path.is_symlink() or not messages_path.is_file():
        raise ValueError("capture message file is unavailable or unsafe")
    entries: list[dict[str, Any]] = []
    fd = os.open(messages_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            entry = _normalize_entry(raw, scope, line_number)
            if entry is not None:
                entries.append(entry)
    if not entries:
        return
    entries.sort(key=lambda row: (row["ts"] is None, row["ts"] or 0.0, row["source_line"]))
    page = root / "sessions" / _session_page_name(scope)
    _write_diary_text_atomic(root, page, _render_session_page(scope, entries))


def render_sessions(diary_root: Path | str) -> int:
    root = _validate_diary_root(diary_root)
    by_session: dict[str, list[dict[str, Any]]] = {}
    for entry in _iter_entries(root):
        by_session.setdefault(entry["source_scope"], []).append(entry)
    pages_written = 0
    for scope, entries in by_session.items():
        entries.sort(key=lambda row: (row["ts"] is None, row["ts"] or 0.0, row["source_line"]))
        page_name = _session_page_name(scope)
        _write_diary_text_atomic(root, root / "sessions" / page_name, _render_session_page(scope, entries))
        pages_written += 1
    return pages_written


def _session_page_name(scope: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", scope).strip("-.") or "session"
    digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:48]}-{digest}.md"


def _render_session_page(scope: str, rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Session: {_md_inline(scope)}",
        "",
        "Generated from visible user prompts and final assistant responses. Do not edit this file; use `notes.md` for manual notes.",
        "",
    ]
    for row in rows:
        stamp = _format_timestamp(row["ts"])
        label = "User prompt" if row["role"] == "user" else "Final assistant response"
        source_key = f"{scope}/messages.jsonl:{row['source_line']}"
        lines.extend([
            f"## {stamp} — {label}",
            "",
            f"- Source: `{_md_inline(source_key)}`",
            f"- Session: `{_md_inline(row['session_id'] or 'unavailable')}` · turn: `{row['turn_index'] if row['turn_index'] is not None else 'unavailable'}`",
        ])
        if row["prompt_id"]:
            lines.append(f"- Prompt ID: `{_md_inline(row['prompt_id'])}`")
        flags = []
        if row["redactions"]:
            flags.append(f"redacted: {row['redactions']}")
        if row["truncated"]:
            flags.append("truncated")
        if row["text"] is None:
            flags.append("text unavailable")
        if row["turn_status"]:
            flags.append(f"turn: {row['turn_status']}")
        if flags:
            lines.append("- Markers: " + ", ".join(flags))
        lines.extend(["", "<pre>" + _safe_pre(row["text"]) + "</pre>" if row["text"] is not None else "_Text unavailable._", ""])
    return "\n".join(lines)


def _read_commits(project_root: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["git", "-C", str(project_root), "log", "--no-renames", "--date=iso-strict", "--format=%H%x09%cI%x09%s", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in result.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and len(parts[0]) == 40:
            if current is not None:
                _keep_commit(commits, current)
            current = {"hash": parts[0], "date": _utc_date(parts[1]), "subject": parts[2], "files": []}
        elif current is not None and line.strip():
            current["files"].append(line.strip())
    if current is not None:
        _keep_commit(commits, current)
    return commits


def _keep_commit(commits: list[dict[str, Any]], commit: dict[str, Any]) -> None:
    files = commit["files"]
    if files and all(path.startswith("developer_diary/") for path in files):
        return
    commits.append(commit)


def _render_commits(commits: list[dict[str, Any]]) -> str:
    lines = [
        "# Committed project changes",
        "",
        "Git metadata only: this list does not infer which prompt caused a commit. Diary-only commits are omitted to avoid a self-referencing log.",
        "",
        "| UTC date | Commit | Subject | Changed files |",
        "|---|---|---|---|",
    ]
    for item in commits:
        paths = ", ".join(_md_inline(path) for path in item["files"])
        lines.append(f"| {item['date']} | `{item['hash'][:12]}` | {_md_cell(item['subject'])} | {paths} |")
    if not commits:
        lines.append("| — | — | No commits found | — |")
    return "\n".join(lines) + "\n"


def _month_key(stamp: float | None) -> str:
    return datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m") if stamp is not None else "undated"


def _format_timestamp(stamp: float | None) -> str:
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z") if stamp is not None else "timestamp unavailable"


def _utc_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except ValueError:
        return value


def _safe_pre(value: str) -> str:
    visible = "".join(
        char if char.isprintable() or char in "\n\t" else f"\\u{ord(char):04x}"
        for char in value
    )
    return html.escape(visible, quote=False)


def _md_inline(value: str) -> str:
    return value.replace("`", "&#96;").replace("|", "&#124;").replace("\n", " ")


def _md_cell(value: str) -> str:
    return html.escape(value, quote=False).replace("|", "&#124;").replace("\n", " ")


def _write_diary_text_atomic(diary_root: Path, path: Path, text: str) -> None:
    root = _validate_diary_root(diary_root)
    if not path.is_relative_to(root):
        raise ValueError("diary output is outside the diary root")
    _ensure_safe_directory(root, path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("refusing to replace an unsafe diary file")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
