"""Task orchestration service."""

import asyncio
from collections.abc import Callable
from time import monotonic
from uuid import uuid4

from sqlalchemy.orm import Session

from app.graph.workflow import build_graph
from app.infra.logger import get_logger
from app.services.task_repository import TaskRepository
from app.services.task_status import status_payload

logger = get_logger(__name__)


class TaskLimitError(RuntimeError):
    """Raised when the in-process task queue is full."""


class TaskService:
    """Create, run, and query research tasks."""

    def __init__(
        self,
        container,
        session_factory: Callable[[], Session],
        *,
        run_background: bool = True,
    ) -> None:
        self.container = container
        self.session_factory = session_factory
        self.repository = TaskRepository(session_factory)
        self.graph = build_graph(container, on_stage=self._on_workflow_stage)
        self.run_background = run_background
        self._tasks: dict[str, dict] = {}
        self._background_tasks: dict[str, asyncio.Task[None]] = {}
        self._task_semaphore = asyncio.Semaphore(container.settings.max_concurrent_tasks)
        self._max_queued_tasks = container.settings.max_queued_tasks
        self._mark_stale_running_tasks()

    async def create_task(
        self,
        query: str,
        competitors: list[str] | None = None,
        dimensions: list[str] | None = None,
    ) -> str:
        """Create and start a task.

        Args:
            query: User query.
            competitors: Optional user-selected competitors.
            dimensions: Optional requested dimensions.

        Returns:
            Created task identifier.
        """
        if self.repository.active_task_count() >= self._max_queued_tasks:
            raise TaskLimitError("too many pending or running tasks; please retry later")

        task_id = f"task_{uuid4().hex[:12]}"
        self._create_row(task_id, query)
        self._tasks[task_id] = status_payload(
            status="PENDING",
            stage="queued",
            issues=[],
            progress=0.0,
            started_at=None,
        )
        args = (task_id, query, competitors or [], dimensions or [])
        if self.run_background:
            task = asyncio.create_task(self._run_task(*args))
            self._background_tasks[task_id] = task
            task.add_done_callback(self._task_done_callback(task_id))
        else:
            await self._run_task(*args)
        return task_id

    async def _run_task(
        self,
        task_id: str,
        query: str,
        competitors: list[str],
        dimensions: list[str],
    ) -> None:
        try:
            async with self._task_semaphore:
                await self._execute_task(task_id, query, competitors, dimensions)
        except asyncio.CancelledError:
            if self._tasks.get(task_id, {}).get("status") != "FAILED":
                self._mark_failed(task_id, "task was cancelled before it could start")
            raise

    async def _execute_task(
        self,
        task_id: str,
        query: str,
        competitors: list[str],
        dimensions: list[str],
    ) -> None:
        self._tasks.setdefault(task_id, {})["started_monotonic"] = monotonic()
        self._update_status(task_id, "RUNNING", "planner", [], progress=0.05)
        try:
            final = await self.graph.ainvoke(
                {
                    "task_id": task_id,
                    "user_query": query,
                    "requested_competitors": competitors,
                    "requested_dimensions": dimensions,
                    "max_iterations": self.container.settings.max_iterations,
                    "sufficiency_threshold": self.container.settings.sufficiency_threshold,
                    "token_usage": {},
                }
            )
            self._persist(task_id, final)
            self._update_status(
                task_id,
                final.get("task_status", "COMPLETED"),
                final.get("current_stage"),
                final.get("issues", []),
                progress=1.0,
            )
        except asyncio.CancelledError:
            message = "task was cancelled before completion"
            logger.warning("task_cancelled", extra={"task_id": task_id})
            self._mark_failed(task_id, message)
            raise
        except Exception as exc:
            logger.exception("task_failed", extra={"task_id": task_id})
            self._mark_failed(task_id, str(exc))

    def _task_done(self, task_id: str, completed: asyncio.Task[None]) -> None:
        self._background_tasks.pop(task_id, None)
        if completed.cancelled():
            return
        try:
            completed.result()
        except Exception as exc:
            logger.warning(
                "background_task_error_consumed",
                extra={"task_id": task_id, "error": str(exc)},
            )

    def _task_done_callback(self, task_id: str) -> Callable[[asyncio.Task[None]], None]:
        def _callback(completed: asyncio.Task[None]) -> None:
            self._task_done(task_id, completed)

        return _callback

    def _on_workflow_stage(
        self,
        state: dict,
        stage: str,
        index: int,
        total: int,
    ) -> None:
        task_id = state.get("task_id")
        if not task_id:
            return
        base = 0.05
        progress = base + (index / max(total, 1)) * 0.9
        self._update_status(
            str(task_id),
            "RUNNING",
            stage,
            list(state.get("issues", [])),
            progress=progress,
        )

    def _create_row(self, task_id: str, query: str) -> None:
        self.repository.create_row(task_id, query)

    def _persist(self, task_id: str, state: dict) -> None:
        self.repository.persist_result(task_id, state)

    def _update_status(
        self,
        task_id: str,
        status: str,
        stage: str | None,
        issues: list,
        *,
        progress: float | None = None,
    ) -> None:
        current = self._tasks.get(task_id, {})
        payload = status_payload(
            status=status,
            stage=stage,
            issues=issues,
            progress=progress if progress is not None else current.get("progress", 0.0),
            started_at=current.get("started_monotonic"),
        )
        self._tasks[task_id] = payload
        self.repository.update_status(task_id, status, stage)

    def _mark_failed(self, task_id: str, message: str) -> None:
        self._tasks[task_id] = status_payload(
            status="FAILED",
            stage="failed",
            issues=[message],
            progress=1.0,
            started_at=self._tasks.get(task_id, {}).get("started_monotonic"),
        )
        self.repository.mark_failed(task_id, message)

    def get_status(self, task_id: str) -> dict:
        """Get task status.

        Args:
            task_id: Task identifier.

        Returns:
            Task status dictionary.
        """
        if task_id in self._tasks:
            payload = self._tasks[task_id]
            if payload.get("status") == "RUNNING":
                return status_payload(
                    status=payload["status"],
                    stage=payload.get("stage"),
                    issues=payload.get("issues", []),
                    progress=payload.get("progress", 0.0),
                    started_at=payload.get("started_monotonic"),
                )
            return payload
        return self.repository.get_status(task_id)

    def _mark_stale_running_tasks(self) -> None:
        try:
            self.repository.mark_stale_running_tasks()
        except Exception as exc:
            logger.warning("stale_task_cleanup_failed", extra={"error": str(exc)})

    def get_report(self, task_id: str) -> dict | None:
        """Get the latest report for a task.

        Args:
            task_id: Task identifier.

        Returns:
            Report payload or None.
        """
        return self.repository.get_report(task_id)
