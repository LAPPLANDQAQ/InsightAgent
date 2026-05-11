# InsightAgent v4 升级提交记录

日期：2026-05-11

> 说明：本文件覆盖旧会话记录，记录本次 InsightAgent v4 升级的提交整理、验证结果和推送前状态；未记录任何真实 API Key、Cookie 或 Token。

## 用户主要诉求

1. 根据三份 v4 规划文档升级本地项目。
2. 严格对照文档中的 36 个 commit 要求补齐代码、测试、文档和 demo。
3. 检查整理所有提交，覆盖旧记录文档。
4. 复查并及时更新 README。
5. 最后推送到 GitHub。

## 本次升级范围

本次升级将 InsightAgent 从既有多 Agent 竞品调研工具，增量升级为：

```text
TODO-driven DeepResearch + Evidence-grounded RAG + Harness Runtime + MCP Server
```

核心能力包括：

- `ResearchTodo` / `ResearchNote` 任务与阶段性结论契约。
- Planner 自动生成 TODO-driven research plan。
- Feature-flagged RAG workflow：`ENABLE_RAG_RESEARCH=true` 时接入 Router、Indexer、Researcher、Summarizer。
- RAG Research Engine：schemas、cleaner、parent-child chunker、SQLite store、sparse/dense/hybrid retriever、RRF、ContextBuilder。
- Retrieval / Citation / Report Quality / Agent Metrics / RAGAs-style 本地评估。
- Harness Runtime：events、trace store、tool registry、policy、runtime wrapper、metrics、replay。
- MCP Server：安全校验、只读 tools、resources、prompts、stdio smoke server。
- 可选增强：reranker、query rewrite、HyDE、CRAG-style correction、adaptive retrieval strategy。
- Streamlit evidence helper 和本地 fake-data demos。

## 提交整理

本次 v4 代码升级已整理为以下提交，当前本地 `main` 在 `origin/main` 之上。

```text
360a5bf test(rag): add strict optional enhancement coverage
efe8b2c test(protocols): add strict harness and MCP acceptance coverage
109050d test(rag): add strict component acceptance coverage
3c0c6f3 feat(eval): add citation coverage and agent metrics checks
49f68c9 test(rag): add end-to-end RAG research chain
65c570f feat(docs): document v4 and add runnable demos
75ebf6c feat(frontend): add evidence viewer helpers
619ef7c feat(rag): add optional retrieval enhancement components
6e58f81 feat(mcp): add safe read-only server tools
7a7ad4f feat(harness): add runtime tracing and policy controls
6b2b005 feat(agents): add feature-flagged RAG workflow
a5bbad9 feat(rag): add core RAG engine and evaluation metrics
6b1cdbd feat(graph): extend workflow state for RAG research
dbd1c0b feat(planner): generate TODO-driven research plan
22daf47 chore: add repository agent instructions
```

本记录和 README 整理会作为后续文档提交追加到上述提交之后。

## 36 项规划完成情况

| 范围 | 状态 |
|---|---|
| Commit 01-05：ResearchTodo / ResearchNote / Planner / TaskSummarizer / WorkflowState | 完成 |
| Commit 06-15：RAG schemas / cleaner / chunker / store / context / sparse / dense / RRF / hybrid / retrieval metrics | 完成 |
| Commit 16-20：ResearchRouter / RAGIndexer / RAGResearcher / feature flag workflow / end-to-end RAG test | 完成 |
| Commit 21-25：Harness events / trace / registry / policy / runtime / metrics / replay | 完成 |
| Commit 26-28：MCP security / read-only tools / stdio server | 完成 |
| Commit 29：citation metrics / report quality / agent metrics / Critic strengthening | 完成 |
| Commit 30：README / docs / runnable demos | 完成 |
| Commit 31-36：reranker / query rewrite / HyDE / CRAG / adaptive strategy / RAGAs-style eval / evidence viewer | 完成 |

## 验证结果

已执行并通过：

```powershell
python -m ruff check app tests examples scripts frontend
python -m mypy app --ignore-missing-imports
python -m pytest -q
```

结果：

- Ruff：All checks passed
- Mypy：Success, no issues found in 116 source files
- Pytest：120 passed
- 仅有本机 `.pytest_cache` 写入权限 warning，不影响测试结果。

## 可运行 demo

```powershell
python examples/rag_research_demo.py
python examples/mcp_stdio_demo.py
python examples/harness_replay_demo.py
```

## 当前注意事项

- README 中的 v4 指标仍以目标值和 `TBD` 实测值分离；没有写入未实测的性能数字。
- `ENABLE_RAG_RESEARCH=false` 时默认保留旧 workflow。
- `ENABLE_RAG_RESEARCH=true` 时启用新 RAG workflow。
- MCP 只暴露安全只读工具，不暴露 shell、任意 SQL、任意文件写入或任意 HTTP fetch。
- 推送前本地仅有本文件和 README 整理改动需要提交。
