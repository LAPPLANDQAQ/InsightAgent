"""Tests for task API request validation."""

import pytest
from pydantic import ValidationError

from app.schemas.task import CreateTaskRequest


def test_create_task_request_rejects_blank_query():
    with pytest.raises(ValidationError):
        CreateTaskRequest(query="  ")


def test_create_task_request_bounds_list_lengths():
    with pytest.raises(ValidationError):
        CreateTaskRequest(query="market", competitors=[f"c{i}" for i in range(11)])

    with pytest.raises(ValidationError):
        CreateTaskRequest(query="market", dimensions=[f"d{i}" for i in range(13)])


def test_create_task_request_strips_list_items():
    request = CreateTaskRequest(
        query=" market ",
        competitors=[" Cursor "],
        dimensions=[" pricing "],
    )

    assert request.query == "market"
    assert request.competitors == ["Cursor"]
    assert request.dimensions == ["pricing"]
