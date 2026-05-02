"""Task orchestration service."""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.graph.workflow import build_graph
from app.infra.db.models import EvidenceRow, Report, SourceRow, Task
from app.infra.logger import get_logger

logger = get_logger(__name__)


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
        self.graph = build_graph(container)
        self.run_background = run_background
        self._tasks: dict[str, dict] = {}

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
        task_id = f"task_{uuid4().hex[:12]}"
        self._create_row(task_id, query)
        self._tasks[task_id] = {"status": "PENDING", "stage": "queued", "issues": []}
        args = (task_id, query, competitors or [], dimensions or [])
        if self.run_background:
            asyncio.create_task(self._run_task(*args))
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
        self._update_status(task_id, "RUNNING", "planner", [])
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
            )
        except Exception as exc:
            logger.exception("task_failed", extra={"task_id": task_id})
            self._mark_failed(task_id, str(exc))

    def _create_row(self, task_id: str, query: str) -> None:
        with self.session_factory() as session:
            session.add(Task(id=task_id, query=query, status="PENDING"))
            session.commit()

    def _persist(self, task_id: str, state: dict) -> None:
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = state.get("task_status", "COMPLETED")
                task.current_stage = state.get("current_stage")
                task.finished_at = datetime.utcnow()
                task.updated_at = datetime.utcnow()
            session.add(
                Report(
                    task_id=task_id,
                    draft_report=state.get("draft_report"),
                    final_report=state.get("final_report"),
                    quality_metrics_json=json.dumps(
                        state.get("sufficiency", {}),
                        ensure_ascii=False,
                    ),
                )
            )
            for competitor in state.get("competitors", []):
                for source in competitor.get("sources", []):
                    session.add(SourceRow(task_id=task_id, **source))
                for evidence in competitor.get("evidences", []):
                    session.add(EvidenceRow(task_id=task_id, **evidence))
            session.commit()

    def _update_status(self, task_id: str, status: str, stage: str | None, issues: list) -> None:
        self._tasks[task_id] = {"status": status, "stage": stage, "issues": issues}
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = status
                task.current_stage = stage
                task.updated_at = datetime.utcnow()
                session.commit()

    def _mark_failed(self, task_id: str, message: str) -> None:
        self._tasks[task_id] = {"status": "FAILED", "stage": "failed", "issues": [message]}
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = "FAILED"
                task.error_message = message
                task.updated_at = datetime.utcnow()
                session.commit()

    def get_status(self, task_id: str) -> dict:
        """Get task status.

        Args:
            task_id: Task identifier.

        Returns:
            Task status dictionary.
        """
        if task_id in self._tasks:
            return self._tasks[task_id]
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task is None:
                return {"status": "NOT_FOUND"}
            return {"status": task.status, "stage": task.current_stage, "issues": []}

    def get_report(self, task_id: str) -> dict | None:
        """Get the latest report for a task.

        Args:
            task_id: Task identifier.

        Returns:
            Report payload or None.
        """
        with self.session_factory() as session:
            report = (
                session.query(Report)
                .filter_by(task_id=task_id)
                .order_by(Report.id.desc())
                .first()
            )
            if report is None:
                return None
            return {
                "task_id": task_id,
                "report_markdown": report.final_report or report.draft_report or "",
                "quality_metrics": json.loads(report.quality_metrics_json or "{}"),
            }
