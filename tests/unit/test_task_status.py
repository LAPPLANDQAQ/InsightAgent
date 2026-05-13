"""Task status helper tests."""

from app.services.task_status import STAGE_LABELS, status_payload


def test_status_payload_uses_english_stage_label():
    payload = status_payload(
        status="RUNNING",
        stage="planner",
        issues=[],
        progress=0.1,
        started_at=None,
    )

    assert payload["stage_label"] == "Planning"


def test_stage_labels_are_ascii_english():
    assert STAGE_LABELS["failed"] == "Failed"
    assert all(label.isascii() for label in STAGE_LABELS.values())
