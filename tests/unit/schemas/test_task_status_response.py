"""Task status response schema tests."""

from app.schemas.task import IssueDetail, TaskStatusResponse


def test_task_status_response_keeps_legacy_issues_and_structured_default():
    response = TaskStatusResponse(
        task_id="task_1",
        status="FAILED",
        issues=["provider unavailable"],
    )

    assert response.issues == ["provider unavailable"]
    assert response.structured_issues == []


def test_task_status_response_accepts_structured_issues():
    response = TaskStatusResponse(
        task_id="task_1",
        status="FAILED",
        issues=["task cancelled by user"],
        structured_issues=[
            IssueDetail(
                type="cancellation",
                severity="warning",
                stage="failed",
                message="task cancelled by user",
            )
        ],
    )

    assert response.structured_issues[0].type == "cancellation"
