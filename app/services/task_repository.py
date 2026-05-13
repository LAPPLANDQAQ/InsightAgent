"""Task persistence helpers."""

import json
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.infra.db.models import EvidenceRow, Report, SourceRow, Task
from app.infra.logger import get_logger
from app.services.task_status import STALE_RUNNING_MESSAGE, status_payload

logger = get_logger(__name__)
ACTIVE_TASK_STATUSES = {"PENDING", "RUNNING"}


class TaskRepository:
    """Persistence boundary for task lifecycle data."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    def create_row(self, task_id: str, query: str) -> None:
        """Persist a newly queued task row."""
        with self.session_factory() as session:
            session.add(Task(id=task_id, query=query, status="PENDING"))
            session.commit()

    def persist_result(self, task_id: str, state: dict) -> None:
        """Persist a completed workflow state."""
        with self.session_factory() as session:
            try:
                task = session.get(Task, task_id)
                if task:
                    task.status = state.get("task_status", "COMPLETED")
                    task.current_stage = state.get("current_stage")
                    task.error_message = None
                    task.finished_at = datetime.now(UTC)
                    task.updated_at = datetime.now(UTC)
                session.add(
                    Report(
                        task_id=task_id,
                        draft_report=state.get("draft_report"),
                        final_report=state.get("final_report"),
                        quality_metrics_json=json.dumps(
                            _quality_metrics(state),
                            ensure_ascii=False,
                        ),
                    )
                )
                for competitor in state.get("competitors", []):
                    for source in competitor.get("sources", []):
                        session.add(SourceRow(**{**source, "task_id": task_id}))
                    for evidence in competitor.get("evidences", []):
                        session.add(EvidenceRow(**{**evidence, "task_id": task_id}))
                session.commit()
            except Exception:
                session.rollback()
                raise

    def update_status(self, task_id: str, status: str, stage: str | None) -> None:
        """Persist a status and stage update."""
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = status
                task.current_stage = stage
                task.updated_at = datetime.now(UTC)
                session.commit()

    def mark_failed(self, task_id: str, message: str) -> None:
        """Persist task failure details."""
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = "FAILED"
                task.current_stage = "failed"
                task.error_message = message
                task.updated_at = datetime.now(UTC)
                task.finished_at = datetime.now(UTC)
                session.commit()

    def get_status(self, task_id: str) -> dict:
        """Return persisted task status, marking orphaned running rows failed."""
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task is None:
                return {"status": "NOT_FOUND"}
            if task.status == "RUNNING":
                last_stage = task.current_stage or "unknown"
                message = STALE_RUNNING_MESSAGE.format(stage=last_stage)
                task.status = "FAILED"
                task.current_stage = "failed"
                task.error_message = message
                task.updated_at = datetime.now(UTC)
                session.commit()
                return status_payload(
                    status="FAILED",
                    stage="failed",
                    issues=[message],
                    progress=1.0,
                    started_at=None,
                    structured_issues=[
                        {
                            "type": "stale_restart",
                            "severity": "error",
                            "stage": last_stage,
                            "message": message,
                        }
                    ],
                )
            progress = 1.0 if task.status in {"COMPLETED", "COMPLETED_WITH_WARNINGS"} else 0.0
            return status_payload(
                status=task.status,
                stage=task.current_stage,
                issues=[task.error_message] if task.error_message else [],
                progress=progress,
                started_at=None,
            )

    def mark_stale_running_tasks(self) -> None:
        """Mark old RUNNING rows failed after process startup."""
        with self.session_factory() as session:
            rows = session.query(Task).filter_by(status="RUNNING").all()
            for task in rows:
                last_stage = task.current_stage or "unknown"
                task.status = "FAILED"
                task.current_stage = "failed"
                task.error_message = STALE_RUNNING_MESSAGE.format(stage=last_stage)
                task.updated_at = datetime.now(UTC)
            if rows:
                session.commit()

    def active_task_count(self) -> int:
        """Return active pending/running task count."""
        with self.session_factory() as session:
            return int(session.query(Task).filter(Task.status.in_(ACTIVE_TASK_STATUSES)).count())

    def get_report(self, task_id: str) -> dict | None:
        """Return the latest report for a task."""
        with self.session_factory() as session:
            report = (
                session.query(Report)
                .filter_by(task_id=task_id)
                .order_by(Report.id.desc())
                .first()
            )
            if report is None:
                return None
            try:
                quality_metrics = json.loads(report.quality_metrics_json or "{}")
            except json.JSONDecodeError as exc:
                logger.warning(
                    "report_quality_metrics_decode_failed",
                    extra={"task_id": task_id, "error": str(exc)},
                )
                quality_metrics = {"error": "report quality metrics are malformed"}
            return {
                "task_id": task_id,
                "report_markdown": report.final_report or report.draft_report or "",
                "quality_metrics": quality_metrics,
            }


def _quality_metrics(state: dict) -> dict:
    sufficiency = dict(state.get("sufficiency", {}))
    sufficiency["critic_issues"] = list(state.get("critic_issues", []))
    sufficiency["issues"] = list(state.get("issues", []))
    return sufficiency
