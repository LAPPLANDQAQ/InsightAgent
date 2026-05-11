# InsightAgent v4 Architecture

InsightAgent keeps the existing FastAPI, Streamlit, LangGraph, and five-agent workflow, then adds v4 as an incremental layer.

```text
api -> services -> graph -> agents -> tools/rag/harness -> infra
```

The default workflow remains Planner -> Researcher -> Analyst -> Writer -> Critic. When `ENABLE_RAG_RESEARCH=true`, the graph uses Planner -> ResearchRouter -> RAGIndexer -> RAGResearcher -> TaskSummarizer -> Analyst -> Writer -> Critic.

The v4 data flow is TODO-driven: Planner emits `ResearchTodo`, RAG agents retrieve evidence-grounded chunks, TaskSummarizer emits `ResearchNote`, and Writer/Critic operate on evidence ids.
