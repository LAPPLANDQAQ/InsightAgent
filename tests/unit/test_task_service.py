"""TaskService persistence tests."""

from app.infra.db.models import EvidenceRow, Task
from app.infra.db.session import build_engine, build_session_factory
from app.schemas.report import ReportResponse
from app.services.task_service import TaskService
from app.services.task_status import STALE_RUNNING_MESSAGE


def _service(container_with_stubs) -> tuple[TaskService, object]:
    engine = build_engine("sqlite:///:memory:")
    session_factory = build_session_factory(engine)
    return TaskService(container_with_stubs, session_factory, run_background=False), session_factory


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
