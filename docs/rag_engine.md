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
