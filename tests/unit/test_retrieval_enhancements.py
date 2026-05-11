"""Tests for optional retrieval enhancement components."""

import pytest
from pydantic import ValidationError

from app.agents.rag_corrector import RAGCorrector
from app.rag.quality.retrieval_quality_grader import RetrievalQualityGrader
from app.rag.query.hyde import HyDEGenerator
from app.rag.query.query_rewriter import QueryRewriter
from app.rag.rerankers.cross_encoder_reranker import CrossEncoderReranker
from app.rag.rerankers.fake_reranker import FakeReranker
from app.rag.schemas import ChildChunk, RetrievedChunk
from app.rag.strategy.retrieval_strategy_router import (
    RetrievalStrategyConfig,
    RetrievalStrategyRouter,
)


def _retrieved(score=0.8):
    chunk = ChildChunk(
        chunk_id="chunk_1",
        parent_doc_id="parent_1",
        task_id="task_1",
        source_id="src_1",
        source_url="https://example.com",
        text="Cursor pricing",
        chunk_index=0,
    )
    return RetrievedChunk(chunk=chunk, retriever_name="test", rank=1, score=score)


def test_fake_and_cross_encoder_rerankers_do_not_require_models():
    candidates = [_retrieved(0.1)]

    assert FakeReranker().rerank("Cursor pricing", candidates)[0].rerank_score is not None
    assert CrossEncoderReranker().rerank("query", candidates, top_n=1)


def test_query_rewriter_and_hyde_fallback():
    variants = QueryRewriter().rewrite(
        "Cursor pricing",
        dimension="pricing",
        competitor_name="Cursor",
    )

    assert variants[0] == "Cursor pricing"
    assert len(variants) >= 2


@pytest.mark.asyncio
async def test_hyde_generator_fallback():
    text = await HyDEGenerator().generate("Cursor pricing", dimension="pricing")

    assert "Cursor pricing" in text


@pytest.mark.asyncio
async def test_rag_corrector_grades_retrieval():
    result = await RAGCorrector().run(
        {"user_query": "q", "retrieved_chunks": [_retrieved().model_dump()]}
    )

    assert result["rag_metrics"]["retrieval_quality_grade"] == "correct"


def test_retrieval_quality_and_strategy_router():
    grader = RetrievalQualityGrader()
    router = RetrievalStrategyRouter()

    assert grader.grade("q", [_retrieved(0.4)]) == "ambiguous"
    assert router.route("pricing").sparse_weight > router.route("pricing").dense_weight
    assert router.route("architecture").dense_weight > router.route("architecture").sparse_weight
    assert router.route("risk").freshness_hint
    with pytest.raises(ValidationError):
        RetrievalStrategyConfig(
            strategy_name="bad",
            sparse_weight=0,
            dense_weight=0,
            sparse_top_k=1,
            dense_top_k=1,
            final_top_k=1,
        )
