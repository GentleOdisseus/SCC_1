"""Observer: сбор телеметрии. См. docs/02_architecture/observer.md."""
from scc.observer.events import EventKind, TelemetryEvent
from scc.observer.telemetry import TelemetryLog

__all__ = ["EventKind", "TelemetryEvent", "TelemetryLog"]
