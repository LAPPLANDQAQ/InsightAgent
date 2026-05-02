# InsightAgent

InsightAgent 是一个基于 FastAPI、LangGraph 风格工作流、Pydantic v2 和 SQLAlchemy 的多 Agent 竞品分析系统。系统输入赛道或产品方向后，会规划调研维度、搜索公开资料、抓取网页、抽取证据、生成分析结论，并输出带证据引用的 Markdown 报告。

## 当前状态

项目已完成从基础骨架到可离线跑通的端到端流程：

- 配置层：运行时模型守卫，只允许千问/QwQ 系列模型作为业务 LLM。
- 协议层：LLM、搜索、抓取、缓存均通过 Protocol 抽象。
- 基础设施：内存缓存、SQLite 缓存、结构化 JSON 日志、搜索聚合、网页抓取、DashScope 千问客户端。
- 工具层：搜索、网页抓取、证据抽取、来源分类、充分性评估、去重。
- Agent 层：Planner、Researcher、Analyst、Writer、Critic。
- 服务层：TaskService、FastAPI 路由、SQLite 持久化。
- 前端与脚本：Streamlit 前端、演示缓存预热脚本、离线 E2E 测试。

## 架构分层

项目遵循单向依赖：

```text
api -> services -> graph -> agents -> tools -> infra
```

关键边界：

- Agent 不直接导入外部 SDK，也不导入 infra 实现类。
- Tool 之间不互相调用，只有 `app.tools.dedup` 作为纯函数例外。
- OpenAI SDK 只允许在 `app/infra/llm/qwen_dashscope_client.py` 中作为 DashScope 兼容传输层使用。
- 业务代码只传 `model_role`，不硬编码真实模型名。

## 快速开始

```powershell
cp .env.example .env
```

编辑 `.env`，至少配置：

```text
DASHSCOPE_API_KEY=你的 DashScope Key
LLM_HEAVY_MODEL=qwen-max
LLM_LIGHT_MODEL=qwen-turbo
LLM_FALLBACK_MODEL=qwen-plus
```

安装依赖：

```powershell
pip install -e ".[dev]"
```

运行测试：

```powershell
python -m pytest tests/architecture/ tests/unit/ tests/integration/ tests/e2e/ -v
python -m ruff check app/ tests/
```

启动后端：

```powershell
uvicorn app.main:app --reload
```

启动前端：

```powershell
streamlit run frontend/streamlit_app.py
```

## API

创建任务：

```http
POST /api/tasks
```

请求体：

```json
{
  "query": "AI 编程助手赛道",
  "competitors": ["Cursor", "GitHub Copilot"],
  "dimensions": ["pricing", "features", "ecosystem"]
}
```

查询状态：

```http
GET /api/tasks/{task_id}
```

获取报告：

```http
GET /api/tasks/{task_id}/report
```

## 演示脚本

预热演示缓存：

```powershell
python scripts/preload_demo_cache.py
```

运行最小服务烟囱：

```powershell
python scripts/smoke_live.py
```

## Docker

```powershell
docker compose up --build
```

服务端口：

- API：http://localhost:8000
- Streamlit：http://localhost:8501

## 测试说明

离线测试全部使用 Fake/Stub，不访问外网：

- `tests/architecture/`：架构边界、模型守卫、文件大小、docstring。
- `tests/unit/`：Schema、缓存、日志、搜索抓取、千问客户端、工具层。
- `tests/integration/`：工作流集成。
- `tests/e2e/`：完整离线烟囱。

## 当前限制

- 真实搜索和抓取质量取决于第三方搜索结果与公开网页可访问性。
- 当前 Critic 默认使用规则检查，LLM Critic 入口保留但默认关闭。
- 报告生成已具备规则兜底，真实质量依赖千问模型输出和证据覆盖。
- SQLite 适合本地演示，生产部署建议替换为正式数据库并补充迁移流程。
