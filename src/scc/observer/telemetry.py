"""Append-only журнал событий (JSONL) для воспроизводимых прогонов."""
from __future__ import annotations

import json
from pathlib import Path

from scc.observer.events import EventKind, TelemetryEvent


class TelemetryLog:
    def __init__(self, path: str | Path | None = None):
        self.events: list[TelemetryEvent] = []
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: TelemetryEvent) -> None:
        self.events.append(event)
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def tokens(self, node_id: str | None = None) -> int:
        return sum(e.tokens for e in self.events if node_id is None or e.node_id == node_id)

    def by_kind(self, kind: EventKind) -> list[TelemetryEvent]:
        return [e for e in self.events if e.kind == kind]
