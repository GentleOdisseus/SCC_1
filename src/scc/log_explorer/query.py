"""Small, allowlisted query grammar for Explorer search."""
from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import datetime, timezone

from scc.log_explorer.reader import Record

_FIELDS = {"source", "type", "session", "tool", "requirement", "status", "after", "before"}


class QueryError(ValueError):
    """A query contains unsupported syntax or a malformed value."""


@dataclass(frozen=True)
class Clause:
    field: str | None
    value: str
    timestamp: float | None = None


@dataclass(frozen=True)
class Query:
    clauses: tuple[Clause, ...] = ()

    def matches(self, record: Record) -> bool:
        return all(_matches(clause, record) for clause in self.clauses)


def parse_query(text: str) -> Query:
    """Parse whitespace-separated AND terms; only declared selectors are legal."""
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError as exc:
        raise QueryError("unclosed quote") from exc
    clauses: list[Clause] = []
    for token in tokens:
        if ":" not in token:
            clauses.append(Clause(None, token.casefold()))
            continue
        field, value = token.split(":", 1)
        field = field.casefold()
        if field not in _FIELDS:
            raise QueryError(f"unknown field: {field}")
        if not value:
            raise QueryError(f"missing value for {field}")
        if field in {"after", "before"}:
            timestamp = _parse_datetime(value)
            clauses.append(Clause(field, value, timestamp))
        else:
            clauses.append(Clause(field, value.casefold()))
    return Query(tuple(clauses))


def _matches(clause: Clause, record: Record) -> bool:
    if clause.field is None:
        return clause.value in record.searchable.casefold()
    field, value = clause.field, clause.value
    if field == "after":
        return record.ts is not None and record.ts > clause.timestamp
    if field == "before":
        return record.ts is not None and record.ts < clause.timestamp
    fields = record.fields
    if field == "source":
        candidates = (record.source,)
    elif field == "type":
        candidates = (record.record_type, fields.get("kind"), fields.get("event_name"), fields.get("role"))
    elif field == "session":
        candidates = (fields.get("session_id"),)
    elif field == "tool":
        candidates = (fields.get("tool_name"),)
    elif field == "requirement":
        candidates = tuple(item.get("id") for item in fields.get("requirements", []) if isinstance(item, dict))
    elif field == "status":
        requirements = fields.get("requirements", [])
        candidates = (fields.get("outcome"), fields.get("status"), *(item.get("status") for item in requirements if isinstance(item, dict)))
    else:
        return False
    return any(isinstance(item, str) and item.casefold() == value for item in candidates)


def _parse_datetime(value: str) -> float:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise QueryError("after/before must use ISO-8601 date or datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()
