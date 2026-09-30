"""Small curses interface for browsing a local run catalog."""
from __future__ import annotations

import curses
import textwrap
import time
from pathlib import Path
from typing import Any

from scc.log_explorer.catalog import filter_records, list_runs
from scc.log_explorer.process_log import ProcessLogPage, read_process_log_page
from scc.log_explorer.query import Query, QueryError, parse_query
from scc.log_explorer.reader import Record, RunInfo

def run_ui(stdscr: Any, runs_root: Path) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    stdscr.keypad(True)
    mode = "runs"
    runs = list_runs(str(runs_root))
    selected_run = 0
    selected_record = 0
    detail_scroll = 0
    query_text = ""
    query_error = ""
    query = parse_query("")
    log_query_text = ""
    log_query_error = ""
    log_query = parse_query("")
    log_page = ProcessLogPage((), 0, 0, 0, "not opened")
    selected_log_record = 0
    detail_record: Record | None = None
    detail_parent = "timeline"

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if mode == "runs":
            _draw_runs(stdscr, runs, selected_run, runs_root, height, width)
        elif mode == "timeline" and runs:
            run = runs[selected_run]
            records = filter_records(run.records, query)
            selected_record = min(selected_record, max(0, len(records) - 1))
            _draw_timeline(stdscr, run, records, selected_record, query_text, query_error, height, width)
        elif mode == "process_log" and runs:
            selected_log_record = min(selected_log_record, max(0, len(log_page.records) - 1))
            _draw_process_log(stdscr, runs[selected_run], log_page, selected_log_record, log_query_text, log_query_error, height, width)
        elif mode == "detail" and runs and detail_record is not None:
            detail_scroll = _draw_detail(stdscr, runs[selected_run], detail_record, detail_scroll, height, width, query_text if detail_parent == "timeline" else log_query_text, query_error if detail_parent == "timeline" else log_query_error)
        stdscr.refresh()

        key = stdscr.getch()
        if key == ord("q"):
            return
        elif key == 27:
            if mode == "detail":
                mode = detail_parent
                detail_record = None
            elif mode in {"timeline", "process_log"}:
                mode = "runs" if mode == "timeline" else "timeline"
            else:
                return
        elif key == curses.KEY_RESIZE:
            continue
        elif mode == "runs":
            if key in (curses.KEY_UP, ord("k")):
                selected_run = max(0, selected_run - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                selected_run = min(max(0, len(runs) - 1), selected_run + 1)
            elif key in (10, 13, curses.KEY_ENTER) and runs:
                selected_record = 0
                mode = "timeline"
            elif key == ord("r"):
                current_id = runs[selected_run].run_id if runs else None
                runs = list_runs(str(runs_root))
                selected_run = next((i for i, run in enumerate(runs) if run.run_id == current_id), 0)
        elif mode == "timeline":
            visible = filter_records(runs[selected_run].records, query)
            if key in (curses.KEY_UP, ord("k")):
                selected_record = max(0, selected_record - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                selected_record = min(max(0, len(visible) - 1), selected_record + 1)
            elif key in (10, 13, curses.KEY_ENTER) and visible:
                detail_scroll = 0
                detail_record = visible[selected_record]
                detail_parent = "timeline"
                mode = "detail"
            elif key == ord("l"):
                log_query_text = ""
                log_query_error = ""
                log_query = parse_query("")
                log_page = _load_log_page(runs[selected_run], log_query, 0)
                selected_log_record = 0
                mode = "process_log"
            elif key == ord("/"):
                entered = _prompt(stdscr, "Search query: ", query_text)
                query_text = entered
                try:
                    query = parse_query(query_text)
                    query_error = ""
                    selected_record = 0
                except QueryError as exc:
                    query_error = str(exc)
            elif key == ord("f"):
                entered = _prompt(stdscr, "Filters (query): ", query_text)
                try:
                    query = parse_query(entered)
                    query_text, query_error, selected_record = entered, "", 0
                except QueryError as exc:
                    query_text, query_error = entered, str(exc)
            elif key == ord("r"):
                current_id = runs[selected_run].run_id
                runs = list_runs(str(runs_root))
                selected_run = next((i for i, run in enumerate(runs) if run.run_id == current_id), 0)
                selected_record = 0
                if not runs:
                    mode = "runs"
            elif key == ord("b"):
                mode = "runs"
        elif mode == "process_log":
            if key in (curses.KEY_UP, ord("k")):
                selected_log_record = max(0, selected_log_record - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                selected_log_record = min(max(0, len(log_page.records) - 1), selected_log_record + 1)
            elif key in (10, 13, curses.KEY_ENTER) and log_page.records:
                detail_record = log_page.records[selected_log_record]
                detail_parent = "process_log"
                detail_scroll = 0
                mode = "detail"
            elif key in (ord("/"), ord("f")):
                entered = _prompt(stdscr, "Process-log query: ", log_query_text)
                try:
                    log_query = parse_query(entered)
                    log_query_text, log_query_error = entered, ""
                    log_page = _load_log_page(runs[selected_run], log_query, 0)
                    selected_log_record = 0
                except QueryError as exc:
                    log_query_text, log_query_error = entered, str(exc)
            elif key == ord("r"):
                log_page = _load_log_page(runs[selected_run], log_query, log_page.page_index)
                selected_log_record = min(selected_log_record, max(0, len(log_page.records) - 1))
            elif key == ord("n") and log_page.page_index + 1 < log_page.page_count:
                log_page = _load_log_page(runs[selected_run], log_query, log_page.page_index + 1)
                selected_log_record = 0
            elif key == ord("p") and log_page.page_index > 0:
                log_page = _load_log_page(runs[selected_run], log_query, log_page.page_index - 1)
                selected_log_record = 0
            elif key == ord("b"):
                mode = "timeline"
        elif mode == "detail":
            if key in (curses.KEY_UP, ord("k")):
                detail_scroll = max(0, detail_scroll - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                detail_scroll += 1
            elif key in (10, 13, curses.KEY_ENTER, curses.KEY_LEFT):
                mode = detail_parent
                detail_record = None
            elif key == ord("r"):
                current_id = runs[selected_run].run_id
                if detail_parent == "process_log":
                    log_page = _load_log_page(runs[selected_run], log_query, log_page.page_index)
                    selected_log_record = min(selected_log_record, max(0, len(log_page.records) - 1))
                    detail_record = log_page.records[selected_log_record] if log_page.records else None
                    if detail_record is None:
                        mode = "process_log"
                else:
                    identity = detail_record.identity if detail_record else None
                    runs = list_runs(str(runs_root))
                    if not runs:
                        mode = "runs"
                        detail_record = None
                    else:
                        selected_run = next((i for i, run in enumerate(runs) if run.run_id == current_id), 0)
                        new_records = filter_records(runs[selected_run].records, query)
                        selected_record = next((i for i, record in enumerate(new_records) if record.identity == identity), 0)
                        detail_record = new_records[selected_record] if new_records else None
                        if detail_record is None:
                            mode = "timeline"
                detail_scroll = 0


def _load_log_page(run: RunInfo, query: Query, page_index: int) -> ProcessLogPage:
    return read_process_log_page(run.path, run.run_id, query, page_index=page_index)


def _draw_runs(stdscr: Any, runs: list[RunInfo], selected: int, root: Path, height: int, width: int) -> None:
    _add(stdscr, 0, 0, "SCC RUN EXPLORER  ·  read-only", width)
    _add(stdscr, 1, 0, f"root: {root}", width)
    _add(stdscr, 3, 0, f"{'Run':<34} {'Observer':<10} {'Task':<12} {'Verified':<10} Last activity", width)
    if not runs:
        _add(stdscr, 4, 0, "No run directories found (only direct child directories are listed).", width)
    start = max(0, min(selected - max(1, height - 6) // 2, max(0, len(runs) - max(1, height - 6))))
    for row, run in enumerate(runs[start:start + max(1, height - 6)], 4):
        mark = ">" if start + row - 4 == selected else " "
        verified = _format_progress(run.progress, run.goal_reached)
        last = _format_time(run.last_activity)
        _add(stdscr, row, 0, f"{mark} {run.run_id:<32.32} {run.observer_state:<10} {run.task_lifecycle:<12} {verified:<10} {last}", width)
    _add(stdscr, height - 1, 0, "↑/↓ select  Enter open  q quit", width)


def _draw_timeline(stdscr: Any, run: RunInfo, records: list[Record], selected: int, query: str, error: str, height: int, width: int) -> None:
    progress = _format_progress(run.progress, run.goal_reached)
    _add(stdscr, 0, 0, f"Run {run.run_id}", width)
    pid = str(run.observer_pid) if run.observer_pid is not None else "unavailable"
    updated = _format_time(run.observer_updated_at)
    error_label = "yes" if run.observer_error_present else "no"
    started = _format_time(run.observer_started_at)
    _add(stdscr, 1, 0, f"Observer process: {run.observer_state} · PID: {pid} · started: {started} · updated: {updated} · error reported: {error_label}", width)
    _add(stdscr, 2, 0, f"Task-run lifecycle: {run.task_lifecycle}", width)
    goal = "reached" if run.goal_reached is True else "not reached" if run.goal_reached is False else "unavailable"
    _add(stdscr, 3, 0, f"Verifier outcome: progress {_format_progress(run.progress, None)} · goal {goal}", width)
    _add(stdscr, 4, 0, f"Workspace: {run.config.get('workspace', 'unavailable')} · task dir: {run.config.get('task_dir', 'unavailable')}", width)
    project = run.config.get("project_root", "unavailable")
    config_start = _format_time(run.config.get("started_at"))
    _add(stdscr, 5, 0, f"Project root: {project} · observer started: {config_start}", width)
    _add(stdscr, 6, 0, f"Query: {query or '(none)'}", width)
    _add(stdscr, 7, 0, f"Filter: {error}" if error else f"Records: {len(records)}  ·  missing/invalid source files: {len(run.issues)}", width)
    _add(stdscr, 8, 0, f"{'Time':<9} {'Source':<18} Record summary", width)
    visible = max(1, height - 11)
    start = max(0, min(selected - visible // 2, max(0, len(records) - visible)))
    for row, record in enumerate(records[start:start + visible], 9):
        mark = ">" if start + row - 9 == selected else " "
        stamp = time.strftime("%H:%M:%S", time.localtime(record.ts)) if record.ts is not None else "—"
        _add(stdscr, row, 0, f"{mark} {stamp:<8} {record.source:<18.18} {_record_label(record)}", width)
    _add(stdscr, height - 2, 0, "Query fields: source type session tool requirement status after before · implicit AND", width)
    _add(stdscr, height - 1, 0, "↑/↓ select  Enter detail  / search  f filters  l process log  r refresh  b runs  q quit", width)


def _draw_process_log(stdscr: Any, run: RunInfo, page: ProcessLogPage, selected: int, query: str, error: str, height: int, width: int) -> None:
    _add(stdscr, 0, 0, f"Process log · {run.run_id} · {run.path / 'speedometer.log'}", width)
    _add(stdscr, 1, 0, "Raw worker text; this file is not redacted like the visible prompt feed.", width)
    _add(stdscr, 2, 0, f"Query: {query or '(none)'}" + (f" · {error}" if error else ""), width)
    if page.issue:
        status = f"speedometer.log: {page.issue}"
    elif page.total:
        status = f"{page.total} matching lines · page {page.page_index + 1}/{page.page_count} from newest"
    else:
        status = "No matching lines"
    _add(stdscr, 3, 0, status, width)
    _add(stdscr, 4, 0, "Line   Worker log line", width)
    visible = max(1, height - 7)
    start = max(0, min(selected - visible // 2, max(0, len(page.records) - visible)))
    for row, record in enumerate(page.records[start:start + visible], 5):
        mark = ">" if start + row - 5 == selected else " "
        line = _clean_display(record.summary)
        if record.truncated:
            line += " · truncated"
        _add(stdscr, row, 0, f"{mark} {record.line:<6} {line}", width)
    _add(stdscr, height - 2, 0, "Query fields: source:speedometer.log · terms/phrases use AND", width)
    _add(stdscr, height - 1, 0, "↑/↓ select  Enter detail  / search  f filters  r refresh  n older  p newer  b back  q quit", width)


def _draw_detail(stdscr: Any, run: RunInfo, record: Record, scroll: int, height: int, width: int, query: str, error: str) -> int:
    location = f"{record.file}:{record.line}" if record.line else record.file
    lines = [
        f"Detail: {record.source} · {location}",
        f"timestamp: {_format_time(record.ts)} · type: {record.record_type}",
        f"run: {record.run_id}",
    ]
    for key in ("kind", "node_id", "role", "event_name", "session_id", "prompt_id", "turn_index", "turn_status", "tool_name", "outcome", "tokens", "cost_usd", "duration_s", "source", "total_input_tokens", "total_output_tokens", "context_window_size", "used_percentage", "remaining_percentage", "progress", "completion_distance", "progress_per_second", "q_min", "goal_reached"):
        if key in record.fields and record.fields[key] is not None:
            lines.append(f"{key}: {record.fields[key]}")
    if "requirements" in record.fields:
        for requirement in record.fields["requirements"]:
            parts = [f"{key}={requirement[key]}" for key in ("id", "q", "weight", "hard", "status") if key in requirement]
            lines.append("requirement: " + ", ".join(parts))
    quality = record.fields.get("prompt_completeness")
    if isinstance(quality, dict):
        lines.append(f"prompt completeness: {quality.get('score')}")
        for key, value in quality.get("criteria", {}).items():
            lines.append(f"  {key}: {value}")
    usage = record.fields.get("current_usage")
    if isinstance(usage, dict):
        lines.append("current_usage: " + ", ".join(f"{key}={value if value is not None else 'unavailable'}" for key, value in usage.items()))
    if record.redactions:
        lines.append(f"privacy: redacted ({record.redactions})")
    if record.truncated:
        lines.append("display: worker-log line capped at 64 KiB" if record.source == "speedometer.log" else "privacy: truncated")
    if record.text_unavailable:
        lines.append("text: unavailable")
    if record.issue:
        lines.append(f"record: {record.issue}")
    if record.source == "messages" and record.searchable:
        lines.append("visible text:")
        lines.extend(textwrap.wrap(_clean_display(record.searchable), max(1, width - 4)) or [""])
    elif record.source == "speedometer.log":
        lines.append("raw worker log line; not redacted by the prompt adapter:")
        lines.extend(textwrap.wrap(_clean_display(record.searchable), max(1, width - 4)) or ["(blank line)"])
    _add(stdscr, 0, 0, f"Run {run.run_id}", width)
    _add(stdscr, 1, 0, f"Observer process: {run.observer_state}", width)
    _add(stdscr, 2, 0, f"Task-run lifecycle: {run.task_lifecycle}", width)
    goal = "reached" if run.goal_reached is True else "not reached" if run.goal_reached is False else "unavailable"
    _add(stdscr, 3, 0, f"Verifier outcome: progress {_format_progress(run.progress, None)} · goal {goal}", width)
    _add(stdscr, 4, 0, f"Query: {query or '(none)'}" + (f"  ·  {error}" if error else ""), width)
    usable = max(1, height - 7)
    max_scroll = max(0, len(lines) - usable)
    scroll = min(scroll, max_scroll)
    for row, line in enumerate(lines[scroll:scroll + usable], 5):
        _add(stdscr, row, 0, line, width)
    _add(stdscr, height - 1, 0, "↑/↓ scroll  Enter/Esc back  q quit", width)
    return scroll


def _prompt(stdscr: Any, label: str, initial: str) -> str:
    height, width = stdscr.getmaxyx()
    text = list(initial[: max(0, width - len(label) - 2)])
    cursor = len(text)
    while True:
        _add(stdscr, height - 1, 0, label + "".join(text), width)
        stdscr.move(height - 1, min(width - 1, len(label) + cursor))
        stdscr.refresh()
        get_key = getattr(stdscr, "get_wch", stdscr.getch)
        key = get_key()
        if key in ("\n", "\r", 10, 13, curses.KEY_ENTER):
            return "".join(text)
        if key in ("\x1b", 27):
            return initial
        if key in ("\x7f", "\b", curses.KEY_BACKSPACE, 127, 8):
            if cursor:
                cursor -= 1
                text.pop(cursor)
        elif key == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif isinstance(key, str) and len(key) == 1 and key.isprintable() and len(text) < max(0, width - len(label) - 2):
            text.insert(cursor, key)
            cursor += 1
        elif isinstance(key, int) and 32 <= key < getattr(curses, "KEY_MIN", 256) and len(text) < max(0, width - len(label) - 2):
            text.insert(cursor, chr(key))
            cursor += 1


def _record_label(record: Record) -> str:
    if record.issue:
        return record.issue
    label = record.summary or record.record_type
    if record.redactions:
        label += " · redacted"
    if record.truncated:
        label += " · truncated"
    return _clean_display(label)


def _format_progress(progress: float | None, goal_reached: bool | None) -> str:
    if progress is None:
        return "unavailable"
    label = f"{progress:.0%}"
    if goal_reached is not None:
        label += " · goal" if goal_reached else ""
    return label


def _format_time(value: float | None) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value)) if value is not None else "unavailable"


def _clean_display(text: str) -> str:
    return "".join(char if char.isprintable() else " " for char in text)


def _add(window: Any, row: int, col: int, text: str, width: int) -> None:
    if width <= col:
        return
    try:
        window.addnstr(row, col, _clean_display(str(text)), max(0, width - col - 1))
    except curses.error:
        pass
