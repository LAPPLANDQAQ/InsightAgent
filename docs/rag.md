# RAG Research Engine

The RAG layer defines `ParentDocument`, `ChildChunk`, and `RetrievedChunk`.

- `TextCleaner` removes common boilerplate and compacts text.
- `ParentChildChunker` creates stable parent and child ids.
- `SQLiteChunkStore` persists parent/chunk payloads with stdlib `sqlite3`.
- `SparseRetriever` uses token overlap.
- `DenseRetriever` uses deterministic hashing embeddings by default.
- `HybridRetriever` fuses sparse and dense results with RRF.
- `ContextBuilder` renders bounded citation-friendly context.

Tests and demos use deterministic local data only.

## Local Smoke

This smoke uses only local deterministic components and does not access the network:

```python
from app.rag.chunkers.parent_child_chunker import ParentChildChunker
from app.rag.cleaners.text_cleaner import TextCleaner
from app.rag.retrievers.sparse_retriever import SparseRetriever

text = "Accept cookies\n\nCursor pricing includes Pro and Business plans."
cleaned = TextCleaner().clean(text)

result = ParentChildChunker(chunk_size=40, overlap=5).chunk_document(
    task_id="manual_task",
    todo_id="todo_manual",
    source_id="src_cursor_pricing",
    source_url="https://cursor.com/pricing",
    title="Cursor Pricing",
    text=cleaned,
    source_type="pricing_page",
    competitor_name="Cursor",
    dimension="pricing",
)

chunks = result.chunks
results = SparseRetriever(chunks).retrieve("Cursor pricing", top_k=3)

assert "Cursor pricing" in cleaned
assert chunks
assert results
```
