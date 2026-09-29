"""Capture allowlisted Claude Code StatusLine context samples."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


_CONTEXT_FIELDS = (
    "total_input_tokens",
    "total_output_tokens",
    "context_window_size",
    "used_percentage",
    "remaining_percentage",
)
_USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def normalize_statusline_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only context-window counters documented by Claude Code."""
    context = data.get("context_window")
    if not isinstance(context, dict):
        context = {}
    sample: dict[str, Any] = {
        "kind": "context_sample",
        "source": "claude_code_statusline",
        "ts": time.time(),
        "session_id": _bounded_string(data.get("session_id"), 128),
        "prompt_id": _bounded_string(data.get("prompt_id"), 128),
    }
    for field in _CONTEXT_FIELDS:
        sample[field] = _numeric(context.get(field), percentage=field.endswith("percentage"))
    current_usage = context.get("current_usage")
    if isinstance(current_usage, dict):
        sample["current_usage"] = {field: _numeric(current_usage.get(field)) for field in _USAGE_FIELDS}
    else:
        sample["current_usage"] = None
    return sample


def append_statusline_sample(run_dir: str | Path, data: dict[str, Any]) -> dict[str, Any]:
    sample = normalize_statusline_payload(data)
    path = Path(run_dir) / "context_samples.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(sample, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        if os.write(fd, line) != len(line):
            raise OSError("short write while appending context sample")
    finally:
        os.close(fd)
    return sample


def format_statusline(sample: dict[str, Any]) -> str:
    percentage = sample.get("used_percentage")
    used = sample.get("total_input_tokens")
    window = sample.get("context_window_size")
    if percentage is None or used is None or window is None:
        return "SCC context: unavailable"
    return f"SCC context: {percentage:.0f}% · {used:,}/{window:,} input tokens"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scc-speedometer-context")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"scc-speedometer-statusline: invalid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("scc-speedometer-statusline: expected a JSON object", file=sys.stderr)
        return 2
    try:
        sample = append_statusline_sample(args.run_dir, data)
    except OSError as exc:
        print(f"scc-speedometer-statusline: {exc}", file=sys.stderr)
        return 2
    print(format_statusline(sample))
    return 0


def _numeric(value: Any, *, percentage: bool = False) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0 or (percentage and value > 100):
        return None
    return value


def _bounded_string(value: Any, limit: int) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[:limit]


if __name__ == "__main__":
    raise SystemExit(main())
