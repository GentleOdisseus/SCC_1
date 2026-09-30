"""CLI entry point for the standalone local run explorer."""
from __future__ import annotations

import argparse
import curses
import sys
import time
from pathlib import Path

from scc.log_explorer.catalog import list_runs
from scc.log_explorer.ui import run_ui


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scc-explorer",
        description="Browse local Speedometer runs (read-only)",
        epilog=(
            "Search query: terms and quoted phrases use AND; allowed selectors are "
            "source, type, session, tool, requirement, status, after, before. "
            "Example: source:messages collision after:2026-09-01T00:00:00Z"
        ),
    )
    parser.add_argument("--runs-dir", type=Path, default=Path("experiments/runs"), help="run root (default: experiments/runs)")
    parser.add_argument("--list", action="store_true", help="print a run summary and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.runs_dir.expanduser()
    try:
        if args.list:
            for run in list_runs(str(root)):
                progress = "unavailable" if run.progress is None else f"{run.progress:.0%}"
                goal = "reached" if run.goal_reached is True else "not reached" if run.goal_reached is False else "unavailable"
                last = "—" if run.last_activity is None else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run.last_activity))
                print(f"{run.run_id}\t{run.observer_state}\t{run.task_lifecycle}\t{progress}\t{goal}\t{last}")
            return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print("scc-explorer requires a terminal; use --list for a read-only run summary", file=sys.stderr)
            return 2
        curses.wrapper(run_ui, root)
    except (OSError, curses.error) as exc:
        print(f"scc-explorer: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0
