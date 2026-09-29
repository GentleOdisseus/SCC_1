"""Типы телеметрических событий."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    ARTIFACT = "artifact"
    CONTEXT_OP = "context_op"
    EVIDENCE = "evidence"
    SESSION_EVENT = "session_event"


@dataclass
class TelemetryEvent:
    kind: EventKind
    node_id: str
    tokens: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d
