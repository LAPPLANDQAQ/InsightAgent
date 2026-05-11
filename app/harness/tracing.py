"""In-memory trace store."""

from app.schemas.harness import HarnessEvent


class InMemoryTraceStore:
    """Append-only trace store for tests and local demos."""

    def __init__(self) -> None:
        self._events: list[HarnessEvent] = []

    def append(self, event: HarnessEvent) -> None:
        """Append one event preserving insertion order."""
        self._events.append(event)

    def list_by_run(self, run_id: str) -> list[HarnessEvent]:
        """Return events for a run id."""
        return [event for event in self._events if event.run_id == run_id]

    def list_by_task(self, task_id: str) -> list[HarnessEvent]:
        """Return events for a task id."""
        return [event for event in self._events if event.task_id == task_id]
