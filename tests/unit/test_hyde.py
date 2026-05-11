"""Tests for HyDEGenerator."""

import pytest

from app.rag.query.hyde import HyDEGenerator


@pytest.mark.asyncio
async def test_hyde_generator_fallback_without_llm():
    """HyDE fallback returns deterministic hypothetical text."""
    text = await HyDEGenerator().generate("Cursor pricing", dimension="pricing")

    assert "Cursor pricing" in text
