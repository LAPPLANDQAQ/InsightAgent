"""Tests for core RAG engine components."""

from app.rag.chunkers.parent_child_chunker import ParentChildChunker
from app.rag.cleaners.text_cleaner import TextCleaner
from app.rag.context.context_builder import ContextBuilder
from app.rag.index.embedding_client import DeterministicEmbeddingClient
from app.rag.retrievers.dense_retriever import DenseRetriever
from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.retrievers.sparse_retriever import SparseRetriever
from app.rag.schemas import ChildChunk, RetrievedChunk


def _chunk(chunk_id="chunk_1", text="Cursor pricing includes a Pro plan."):
    return ChildChunk(
        chunk_id=chunk_id,
        parent_doc_id="parent_1",
        task_id="task_1",
        source_id="src_1",
        source_url="https://example.com",
        text=text,
        chunk_index=0,
    )


def test_text_cleaner_removes_noise_and_keeps_body():
    text = "Accept cookies\n\nCursor pricing includes Pro.\nFooter"

    cleaned = TextCleaner().clean(text)

    assert "Cursor pricing" in cleaned
    assert "cookies" not in cleaned.lower()


def test_parent_child_chunker_creates_stable_chunks():
    result = ParentChildChunker(chunk_size=20, overlap=5).chunk_document(
        task_id="task_1",
        source_id="src_1",
        source_url="https://example.com",
        title="Title",
        text="Cursor pricing includes Pro and Business plans.",
    )

    assert result.parent.parent_doc_id == "parent_task_1_src_1"
    assert result.chunks
    assert result.chunks[0].chunk_index == 0


def test_sparse_dense_and_hybrid_retrievers_return_matches():
    chunks = [_chunk(), _chunk("chunk_2", "Unrelated ecosystem text.")]

    sparse = SparseRetriever(chunks).retrieve("Cursor pricing", top_k=1)
    dense = DenseRetriever(chunks, DeterministicEmbeddingClient()).retrieve(
        "Cursor pricing",
        top_k=1,
    )
    hybrid = HybridRetriever(chunks).retrieve("Cursor pricing", final_top_k=1)

    assert sparse[0].chunk.chunk_id == "chunk_1"
    assert dense
    assert hybrid[0].rank == 1


def test_context_builder_outputs_headers():
    chunk = _chunk()
    retrieved = RetrievedChunk(chunk=chunk, retriever_name="test", rank=1, score=0.9)

    context = ContextBuilder().build([retrieved], max_chars=200)

    assert "chunk_1" in context
    assert "rank=1" in context
