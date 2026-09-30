"""Run summaries and safe in-memory timeline filtering."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from scc.log_explorer.query import Query
from scc.log_explorer.reader import Record, RunInfo, discover_runs


@dataclass(frozen=True)
class Page:
    records: tuple[Record, ...]
    total: int
    offset: int


def list_runs(runs_root: str) -> list[RunInfo]:
    return discover_runs(runs_root)


def filter_records(records: Iterable[Record], query: Query | None = None) -> list[Record]:
    """Return a stable timeline subset; no persistent index or source writes."""
    return [record for record in records if query is None or query.matches(record)]


def page_records(records: list[Record], offset: int, page_size: int) -> Page:
    size = max(1, page_size)
    start = max(0, min(offset, max(0, len(records) - 1))) if records else 0
    return Page(tuple(records[start:start + size]), len(records), start)
