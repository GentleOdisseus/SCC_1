"""Bounded, read-only access to the optional raw Speedometer worker log."""
from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from scc.log_explorer.query import Query
from scc.log_explorer.reader import Record

MAX_LINE_BYTES = 64 * 1024
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


@dataclass(frozen=True)
class ProcessLogPage:
    records: tuple[Record, ...]
    total: int
    page_index: int
    page_count: int
    issue: str | None = None


def read_process_log_page(
    run_path: Path | str,
    run_id: str,
    query: Query,
    *,
    page_index: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ProcessLogPage:
    """Stream-match one page, with page zero containing the newest matches."""
    page_size = min(MAX_PAGE_SIZE, max(1, page_size))
    page_index = max(0, page_index)
    run_dir = Path(run_path)
    issue = _validate_log_path(run_dir)
    if issue:
        return ProcessLogPage((), 0, 0, 0, issue)

    log_path = run_dir / "speedometer.log"
    try:
        with _open_log(run_dir, log_path) as stream:
            initial_stat = os.fstat(stream.fileno())
            total = sum(1 for record in _iter_records(stream, run_id) if query.matches(record))
        page_count = (total + page_size - 1) // page_size
        if total == 0:
            return ProcessLogPage((), 0, 0, 0, "empty" if initial_stat.st_size == 0 else None)

        page_index = min(page_index, page_count - 1)
        start = max(0, total - (page_index + 1) * page_size)
        end = total - page_index * page_size
        page_records: list[Record] = []
        with _open_log(run_dir, log_path) as stream:
            current_stat = os.fstat(stream.fileno())
            if _stat_key(initial_stat) != _stat_key(current_stat):
                return ProcessLogPage((), total, page_index, page_count, "changed while reading; refresh")
            match_index = 0
            for record in _iter_records(stream, run_id):
                if not query.matches(record):
                    continue
                if start <= match_index < end:
                    page_records.append(record)
                match_index += 1
                if match_index >= end:
                    break
            if _stat_key(current_stat) != _stat_key(os.fstat(stream.fileno())):
                return ProcessLogPage((), total, page_index, page_count, "changed while reading; refresh")
        return ProcessLogPage(tuple(page_records), total, page_index, page_count)
    except FileNotFoundError:
        return ProcessLogPage((), 0, 0, 0, "missing")
    except (OSError, ValueError):
        return ProcessLogPage((), 0, 0, 0, "unreadable")


def _validate_log_path(run_dir: Path) -> str | None:
    log_path = run_dir / "speedometer.log"
    try:
        if run_dir.is_symlink() or not run_dir.is_dir():
            return "run directory unavailable or unsafe"
        if log_path.is_symlink():
            return "unsafe symlink"
        if not log_path.exists():
            return "missing"
        if not log_path.is_file():
            return "unreadable"
        log_path.resolve(strict=True).relative_to(run_dir.resolve(strict=True))
    except (OSError, ValueError):
        return "unavailable or unsafe"
    return None


def _open_log(run_dir: Path, log_path: Path) -> BinaryIO:
    if _validate_log_path(run_dir):
        raise OSError("worker log unavailable or unsafe")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(log_path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("worker log is not a regular file")
        return os.fdopen(fd, "rb")
    except Exception:
        os.close(fd)
        raise


def _iter_records(stream: BinaryIO, run_id: str) -> Iterator[Record]:
    line_number = 0
    while True:
        first = stream.readline(MAX_LINE_BYTES + 1)
        if not first:
            return
        line_number += 1
        truncated = len(first) > MAX_LINE_BYTES
        prefix = first[:MAX_LINE_BYTES]
        if truncated and not first.endswith(b"\n"):
            while True:
                rest = stream.readline(MAX_LINE_BYTES + 1)
                if not rest or rest.endswith(b"\n"):
                    break
        text = prefix.decode("utf-8", errors="replace").rstrip("\r\n")
        summary = text[:160] if text else "(blank line)"
        yield Record(
            run_id=run_id,
            source="speedometer.log",
            file="speedometer.log",
            line=line_number,
            ts=None,
            record_type="worker_log_line",
            fields={"line_number": line_number},
            summary=summary,
            searchable=text,
            truncated=truncated,
        )


def _stat_key(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
