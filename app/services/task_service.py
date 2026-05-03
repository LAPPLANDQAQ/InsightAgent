"""Task orchestration service."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from sqlalchemy.orm import Session

from app.graph.workflow import build_graph
from app.infra.db.models import EvidenceRow, Report, SourceRow, Task
from app.infra.logger import get_logger
from app.services.task_status import STALE_RUNNING_MESSAGE, status_payload

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
        self.graph = build_graph(container, on_stage=self._on_workflow_stage)
        self.run_background = run_background
        self._tasks: dict[str, dict] = {}
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
        self._tasks[task_id]["started_monotonic"] = monotonic()
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
        except Exception as exc:
            logger.exception("task_failed", extra={"task_id": task_id})
            self._mark_failed(task_id, str(exc))

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
        with self.session_factory() as session:
            session.add(Task(id=task_id, query=query, status="PENDING"))
            session.commit()

    def _persist(self, task_id: str, state: dict) -> None:
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = state.get("task_status", "COMPLETED")
                task.current_stage = state.get("current_stage")
                task.finished_at = datetime.now(UTC)
                task.updated_at = datetime.now(UTC)
            session.add(
                Report(
                    task_id=task_id,
                    draft_report=state.get("draft_report"),
                    final_report=state.get("final_report"),
                    quality_metrics_json=json.dumps(
                        self._quality_metrics(state),
                        ensure_ascii=False,
                    ),
                )
            )
            for competitor in state.get("competitors", []):
                for source in competitor.get("sources", []):
                    source_payload = {**source, "task_id": task_id}
                    session.add(SourceRow(**source_payload))
                for evidence in competitor.get("evidences", []):
                    evidence_payload = {**evidence, "task_id": task_id}
                    session.add(EvidenceRow(**evidence_payload))
            session.commit()

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
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = status
                task.current_stage = stage
                task.updated_at = datetime.now(UTC)
                session.commit()

    def _mark_failed(self, task_id: str, message: str) -> None:
        self._tasks[task_id] = status_payload(
            status="FAILED",
            stage="failed",
            issues=[message],
            progress=1.0,
            started_at=self._tasks.get(task_id, {}).get("started_monotonic"),
        )
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = "FAILED"
                task.error_message = message
                task.updated_at = datetime.now(UTC)
                session.commit()

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
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task is None:
                return {"status": "NOT_FOUND"}
            if task.status == "RUNNING":
                task.status = "FAILED"
                task.current_stage = "failed"
                task.error_message = STALE_RUNNING_MESSAGE
                task.updated_at = datetime.now(UTC)
                session.commit()
                return status_payload(
                    status="FAILED",
                    stage="failed",
                    issues=[STALE_RUNNING_MESSAGE],
                    progress=1.0,
                    started_at=None,
                )
            progress = 1.0 if task.status in {"COMPLETED", "COMPLETED_WITH_WARNINGS"} else 0.0
            return status_payload(
                status=task.status,
                stage=task.current_stage,
                issues=[],
                progress=progress,
                started_at=None,
            )

    @staticmethod
    def _quality_metrics(state: dict) -> dict:
        sufficiency = dict(state.get("sufficiency", {}))
        sufficiency["critic_issues"] = list(state.get("critic_issues", []))
        sufficiency["issues"] = list(state.get("issues", []))
        return sufficiency

    def _mark_stale_running_tasks(self) -> None:
        try:
            with self.session_factory() as session:
                rows = session.query(Task).filter_by(status="RUNNING").all()
                for task in rows:
                    task.status = "FAILED"
                    task.current_stage = "failed"
                    task.error_message = STALE_RUNNING_MESSAGE
                    task.updated_at = datetime.now(UTC)
                if rows:
                    session.commit()
        except Exception as exc:
            logger.warning("stale_task_cleanup_failed", extra={"error": str(exc)})

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
