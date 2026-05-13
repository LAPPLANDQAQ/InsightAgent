# InsightAgent v4

InsightAgent 是一个本地运行的 TODO 驱动型 RAG 研究代理，面向竞品分析和公开资料研究。
项目包含 FastAPI 后端、Streamlit 演示界面、LangGraph 工作流、证据感知 RAG 组件、
安全默认的 MCP 适配器，以及本地评估工具。

## 项目范围

稳定本地运行目标：

- 运行时只支持 DeepSeek 作为 LLM 提供方。
- 默认使用 SQLite 保存任务、报告和缓存数据。
- 网页抓取路径包含 SSRF 校验、DNS 校验、重定向校验、响应大小限制和内容类型限制。
- Agent 只负责编排，主路径为 `Planner -> Researcher -> Analyst -> Writer -> Critic`。
- 可选 RAG 路径由 `ResearchRouter`、`RAGIndexer`、`RAGResearcher` 和 `TaskSummarizer` 组成。
- MCP 工具默认只读，默认禁止任意写入、本地危险访问和不安全调用。
- 测试使用伪实现或桩实现，不调用真实 LLM、真实搜索、真实网页、真实 LangFuse 或真实 MCP 客户端。

稳定本地版本暂不覆盖：新增模型提供方、认证、支付、云部署、消息队列、向量数据库、
浏览器自动化测试和前端框架迁移。

## 技术栈

- Python 3.12
- FastAPI
- LangGraph
- Pydantic v2
- SQLAlchemy 2.x
- HTTPX
- Streamlit
- SQLite
- DeepSeek 的 OpenAI 兼容 SDK 传输层

## 架构边界

```text
api -> services -> graph -> agents -> tools/rag/harness/mcp_server -> infra
```

关键约束：

- `agents/` 只做编排，不直接调用外部 SDK、HTTP 客户端、数据库或文件系统副作用。
- 运行时模型名称集中在配置层校验，必须是允许的 DeepSeek 模型。
- OpenAI SDK 只允许在 `app/infra/llm/deepseek_client.py` 中作为 DeepSeek 兼容传输层使用。
- MCP 默认安全：不提供 shell 执行、任意 SQL、任意文件写入、任意 HTTP fetch 或不安全本地文件访问。

## 本地安装

创建并激活 Python 3.12 虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux 或 macOS：

```bash
source .venv/bin/activate
```

安装项目和开发工具：

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

可选 MySQL 实验支持默认不安装：

```bash
pip install -e ".[mysql]"
```

## 环境配置

复制 `.env.example` 为 `.env`，只填写本地运行需要的值。

真实 DeepSeek 运行所需配置：

```env
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your_deepseek_key_here
LLM_HEAVY_MODEL=deepseek-v4-pro
LLM_LIGHT_MODEL=deepseek-v4-flash
LLM_FALLBACK_MODEL=deepseek-v4-flash
```

稳定默认值：

- `DB_URL=sqlite:///./data/insight.db`
- `CACHE_BACKEND=sqlite`
- `ENABLE_RAG_RESEARCH=false`
- `ENABLE_HARNESS=true`
- `ENABLE_MCP_SERVER=true`
- `MCP_ALLOW_WRITE_TOOLS=false`
- `MCP_ALLOW_LOCALHOST=false`
- `TASK_TIMEOUT_SECONDS=900`
- `SEARCH_PROVIDER_TIMEOUT_SECONDS=10.0`

`TAVILY_API_KEY` 可以为空；为空时 Tavily 搜索提供方会被跳过。

## 本地运行

启动 API：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

检查健康状态：

```bash
curl http://127.0.0.1:8000/healthz
```

在第二个终端启动 Streamlit 界面：

```bash
streamlit run frontend/streamlit_app.py --server.port=8501 --server.address=127.0.0.1
```

如果 API 使用其他端口，设置：

```bash
INSIGHT_API_BASE=http://127.0.0.1:8000 streamlit run frontend/streamlit_app.py
```

## API 示例

创建任务：

```bash
curl -X POST http://127.0.0.1:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"AI coding assistant market\",\"competitors\":[\"Cursor\",\"GitHub Copilot\"],\"dimensions\":[\"pricing\",\"features\",\"ecosystem\"]}"
```

查询状态：

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}
```

获取报告：

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}/report
```

## 本地演示

以下演示使用本地确定性 fixture 或安全适配器：

```bash
python examples/rag_research_demo.py
python examples/mcp_stdio_demo.py
python examples/harness_replay_demo.py
```

如需预热演示缓存，可先运行：

```bash
python scripts/preload_demo_cache.py
```

## 验证命令

推荐在提交前运行：

```bash
python -m compileall app
python -m ruff check app tests frontend
python -m mypy app --ignore-missing-imports
python -m pytest tests -q
```

如果本地可用 Docker，可选运行：

```bash
docker compose build
```

## 稳定性与安全改进

当前补丁重点：

- DeepSeek 空内容响应会重试，并可切换到 fallback 模型。
- 任务执行增加全局任务超时，避免长时间占用并发槽。
- 搜索提供方增加单个提供方超时，失败时继续使用其他搜索提供方。
- API 队列满时返回 `Retry-After`，便于前端和客户端退避。
- 配置对象、任务错误、搜索警告、抓取错误和 LLM 诊断统一脱敏 key、token、secret、password、Bearer、`sk-*` 和 `tvly-*`。
- 前端轮询会对 429、503、超时和网络抖动进行短暂重试。
- 状态阶段文案统一为英文，避免中文乱码或混合文案进入 API 响应。

## 指标

下表中的目标值是工程目标，不是实测声明。除非有已提交的评估输出，否则实测值保持 `TBD`。

| 指标 | 目标值 | 实测值 |
|---|---:|---:|
| RAG Hit@5 | >= 0.90 | TBD |
| MRR | >= 0.85 | TBD |
| 引文有效率 | >= 95% | TBD |
| 维度覆盖率 | >= 90% | TBD |
| TODO 完成率 | >= 95% | TBD |

## 文档

- [架构说明](docs/architecture.md)
- [RAG 引擎](docs/rag_engine.md)
- [Harness 运行时](docs/harness_runtime.md)
- [MCP Server](docs/mcp_server.md)
- [评估说明](docs/evaluation.md)
- [稳定版本说明](docs/stable_release_notes.md)
- [延期事项](docs/deferred.md)
- [v4.0.1 修复日志](docs/fix-log-v4.0.1.md)
