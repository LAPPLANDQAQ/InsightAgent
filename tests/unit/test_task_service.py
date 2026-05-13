"""TaskService persistence tests."""

import asyncio

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.infra.db.models import EvidenceRow, Report, Task
from app.infra.db.session import build_engine, build_session_factory
from app.schemas.report import ReportResponse
from app.services.task_repository import TaskRepository
from app.services.task_service import TaskLimitError, TaskService
from app.services.task_status import STALE_RUNNING_MESSAGE


def _service(container_with_stubs) -> tuple[TaskService, object]:
    engine = build_engine("sqlite:///:memory:")
    session_factory = build_session_factory(engine)
    return TaskService(container_with_stubs, session_factory, run_background=False), session_factory


class FakeGraph:
    """Fake graph used to exercise task lifecycle behavior."""

    def __init__(
        self,
        result: dict | None = None,
        error: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self.result = result or {
            "task_status": "COMPLETED",
            "current_stage": "finalize",
            "draft_report": "# draft",
            "final_report": "# final",
            "issues": [],
            "competitors": [],
            "sufficiency": {"score": 1.0},
        }
        self.error = error
        self.delay_seconds = delay_seconds

    async def ainvoke(self, state: dict) -> dict:
        """Return the configured result or raise the configured error."""
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.error:
            raise self.error
        return {**state, **self.result}


@pytest.mark.asyncio
async def test_create_task_persists_success(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    service.graph = FakeGraph()

    task_id = await service.create_task("query")

    status = service.get_status(task_id)
    report = service.get_report(task_id)
    assert status["status"] == "COMPLETED"
    assert status["issues"] == []
    assert report["report_markdown"] == "# final"
    with session_factory() as session:
        task = session.get(Task, task_id)
        assert task.status == "COMPLETED"
        assert task.error_message is None


@pytest.mark.asyncio
async def test_create_task_persists_failure(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    service.graph = FakeGraph(error=RuntimeError("DeepSeek request timed out after retrying"))

    task_id = await service.create_task("query")

    status = service.get_status(task_id)
    assert status["status"] == "FAILED"
    assert "DeepSeek request timed out" in status["issues"][0]
    with session_factory() as session:
        task = session.get(Task, task_id)
        assert task.status == "FAILED"
        assert "DeepSeek request timed out" in task.error_message


@pytest.mark.asyncio
async def test_create_task_failure_redacts_secret_like_message(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    service.graph = FakeGraph(error=RuntimeError("failed with api_key=sk-secret token=abc123"))

    task_id = await service.create_task("query")

    status = service.get_status(task_id)
    assert status["status"] == "FAILED"
    assert "api_key=[REDACTED]" in status["issues"][0]
    assert "token=[REDACTED]" in status["issues"][0]
    assert "sk-secret" not in status["issues"][0]
    assert "abc123" not in status["issues"][0]
    with session_factory() as session:
        task = session.get(Task, task_id)
        assert "sk-secret" not in task.error_message
        assert "abc123" not in task.error_message


@pytest.mark.asyncio
async def test_task_cancellation_marks_failed(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    service.graph = FakeGraph(error=asyncio.CancelledError())
    service._create_row("task_cancel", "query")

    with pytest.raises(asyncio.CancelledError):
        await service._run_task("task_cancel", "query", [], [])

    status = service.get_status("task_cancel")
    assert status["status"] == "FAILED"
    assert "cancelled" in status["issues"][0]
    with session_factory() as session:
        task = session.get(Task, "task_cancel")
        assert task.status == "FAILED"
        assert "cancelled" in task.error_message


@pytest.mark.asyncio
async def test_create_task_rejects_when_queue_is_full(container_with_stubs):
    container_with_stubs.settings.max_queued_tasks = 1
    service, session_factory = _service(container_with_stubs)
    with session_factory() as session:
        session.add(Task(id="task_pending", query="query", status="PENDING"))
        session.commit()

    with pytest.raises(TaskLimitError):
        await service.create_task("another query")


@pytest.mark.asyncio
async def test_task_timeout_marks_failed_and_releases_slot(container_with_stubs):
    container_with_stubs.settings.task_timeout_seconds = 1
    container_with_stubs.settings.max_concurrent_tasks = 1
    service, session_factory = _service(container_with_stubs)
    service.graph = FakeGraph(delay_seconds=2.0)

    timed_out_task = await service.create_task("query")
    timeout_status = service.get_status(timed_out_task)

    service.graph = FakeGraph()
    completed_task = await service.create_task("query")
    completed_status = service.get_status(completed_task)

    assert timeout_status["status"] == "FAILED"
    assert "timed out" in timeout_status["issues"][0]
    assert completed_status["status"] == "COMPLETED"
    with session_factory() as session:
        task = session.get(Task, timed_out_task)
        assert task.status == "FAILED"
        assert "timed out" in task.error_message


def test_persist_accepts_evidence_payload_with_task_id(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    service._create_row("task_real", "query")
    state = {
        "task_status": "COMPLETED",
        "current_stage": "critic",
        "draft_report": "# draft",
        "final_report": "# final",
        "sufficiency": {
            "score": 1.0,
            "is_sufficient": True,
            "missing_dimensions": [],
            "coverage": [
                {
                    "dimension": "pricing",
                    "evidence_count": 1,
                    "sufficient": True,
                }
            ],
        },
        "competitors": [
            {
                "name": "Cursor",
                "sources": [
                    {
                        "source_id": "src_1",
                        "url": "https://cursor.com",
                        "domain": "cursor.com",
                        "title": "Cursor",
                        "source_type": "official",
                        "credibility_score": 0.9,
                        "classification_method": "rule",
                        "published_at": None,
                        "retrieved_at": "2026-01-01T00:00:00Z",
                    }
                ],
                "evidences": [
                    {
                        "task_id": "task_from_evidence",
                        "evidence_id": "ev_1",
                        "competitor_name": "Cursor",
                        "dimension": "pricing",
                        "claim": "Pro plan costs 20 USD per month",
                        "value": "20 USD",
                        "source_id": "src_1",
                        "source_url": "https://cursor.com",
                        "quote": "Cursor Pro costs 20 USD per month.",
                        "confidence": 0.9,
                        "extracted_at": "2026-01-01T00:00:00Z",
                    }
                ],
            }
        ],
    }

    service._persist("task_real", state)

    with session_factory() as session:
        task = session.get(Task, "task_real")
        evidence = session.query(EvidenceRow).one()
        assert task.status == "COMPLETED"
        assert evidence.task_id == "task_real"

    report = service.get_report("task_real")
    response = ReportResponse(
        task_id="task_real",
        status="COMPLETED",
        report_markdown=report["report_markdown"],
        quality_metrics=report["quality_metrics"],
    )
    assert response.quality_metrics["coverage"][0]["dimension"] == "pricing"


def test_get_status_marks_stale_running_task_failed(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    with session_factory() as session:
        session.add(Task(id="task_stale", query="query", status="RUNNING"))
        session.commit()

    status = service.get_status("task_stale")

    assert status["status"] == "FAILED"
    assert status["issues"] == [STALE_RUNNING_MESSAGE]
    with session_factory() as session:
        task = session.get(Task, "task_stale")
        assert task.status == "FAILED"
        assert task.error_message == STALE_RUNNING_MESSAGE


def test_get_status_exposes_persisted_error_message(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    with session_factory() as session:
        session.add(
            Task(
                id="task_failed",
                query="query",
                status="FAILED",
                current_stage="failed",
                error_message="provider unavailable",
            )
        )
        session.commit()

    status = service.get_status("task_failed")

    assert status["status"] == "FAILED"
    assert status["issues"] == ["provider unavailable"]


def test_get_report_handles_malformed_quality_metrics(container_with_stubs):
    service, session_factory = _service(container_with_stubs)
    with session_factory() as session:
        session.add(Task(id="task_report", query="query", status="COMPLETED"))
        session.add(
            Report(
                task_id="task_report",
                final_report="# final",
                quality_metrics_json="{not json",
            )
        )
        session.commit()

    report = service.get_report("task_report")

    assert report["report_markdown"] == "# final"
    assert report["quality_metrics"]["error"] == "report quality metrics are malformed"


def test_repository_rolls_back_failed_persist(container_with_stubs):
    _, session_factory = _service(container_with_stubs)
    repository = TaskRepository(session_factory)
    repository.create_row("task_rollback", "query")
    bad_state = {
        "task_status": "COMPLETED",
        "current_stage": "finalize",
        "final_report": "# final",
        "competitors": [{"sources": [{"source_id": "src_bad"}], "evidences": []}],
    }

    with pytest.raises(SQLAlchemyError):
        repository.persist_result("task_rollback", bad_state)

    with session_factory() as session:
        task = session.get(Task, "task_rollback")
        assert task.status == "PENDING"
        assert session.query(Report).filter_by(task_id="task_rollback").count() == 0
