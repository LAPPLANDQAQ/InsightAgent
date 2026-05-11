# InsightAgent v4

InsightAgent v4 是一个面向竞品调研和公开资料分析的 TODO-driven RAG Research Agent。它保留原有 Planner、Researcher、Analyst、Writer、Critic 工作流，同时新增 `ResearchTodo`、`ResearchNote`、Hybrid Retrieval、Harness Runtime、只读 MCP Server 和本地可运行 demo。

## v4 Highlights

- TODO-driven DeepResearch：Planner 会把调研目标拆成可追踪、可重试的 `ResearchTodo`。
- Evidence-grounded RAG：父子块、Sparse + Dense + RRF 混合检索、ContextBuilder 支撑可追溯证据。
- Harness Runtime：记录 agent/tool events，提供 policy、metrics、replay。
- MCP Server：只暴露安全只读工具，不提供 shell、任意 SQL、任意写文件或任意 HTTP fetch。
- Evaluation：检索指标、引用有效性、维度覆盖率、RAGAs-style 本地规则评估。

## v4 本地 Demo

```bash
python examples/rag_research_demo.py
python examples/mcp_stdio_demo.py
python examples/harness_replay_demo.py
```

## v4 Feature Flags

```bash
ENABLE_RAG_RESEARCH=false
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120
RAG_SPARSE_TOP_K=8
RAG_DENSE_TOP_K=8
RAG_FINAL_TOP_K=5
ENABLE_HARNESS=true
ENABLE_MCP_SERVER=true
```

## v4 Metrics

| 指标 | 目标值 | 实测值 |
|---|---:|---|
| RAG Hit@5 | >= 0.90 | TBD |
| MRR | >= 0.85 | TBD |
| Citation Validity | >= 95% | TBD |
| Dimension Coverage | >= 90% | TBD |
| TODO Completion Rate | >= 95% | TBD |

---

InsightAgent 是一个面向竞品调研和公开资料分析的多 Agent 系统。用户输入赛道、竞品和分析维度后，系统会自动规划调研任务、搜索公开信息、抓取网页、抽取证据、生成分析结论，并在前端输出可阅读的调研文档、维度覆盖雷达图和质量数据。

## 项目亮点

- 多 Agent 协作：Planner、Researcher、Analyst、Writer、Critic 分工明确，职责边界清晰。
- 证据链驱动：搜索、抓取、抽取结果进入结构化证据模型，报告结论可回溯到 `evidence_id`。
- 可视化结果输出：每次调研完成后，前端会展示 Markdown 调研文档、文档下载按钮、维度证据覆盖雷达图和质量指标。
- LangGraph 工作流：用状态图组织调研、充分性检查、分析、写作和质检流程。
- DeepSeek 运行时守卫：业务运行时只接受白名单内的 DeepSeek 模型，避免配置误接入其他模型。
- 稳定性设计：搜索、网页抓取、证据抽取支持缓存；抓取失败会短缓存；服务重启后会处理未完成任务状态。
- 架构可验证：架构测试限制跨层导入、外部 SDK 使用、工具间耦合、文件体积和公共函数文档。
- 前后端完整：FastAPI 提供任务接口，Streamlit 提供可视化操作页面。

## 技术栈

- Python 3.12
- FastAPI
- LangGraph
- Pydantic v2
- SQLAlchemy 2.x
- Streamlit
- HTTPX
- DeepSeek OpenAI-compatible API
- SQLite cache / SQLite task DB

## 架构边界

```text
api -> services -> graph -> agents -> tools -> infra
```

关键约束：

- `agents/` 不直接导入外部 SDK，也不导入 `infra` 实现类。
- 业务代码只使用 `model_role`，真实模型名集中在配置层。
- OpenAI SDK 只作为 DeepSeek OpenAI-compatible 传输层使用。
- `tools/` 之间不互相调用，`app.tools.dedup` 这类纯函数模块除外。

## 目录结构

```text
app/
  api/          FastAPI 路由
  services/     任务编排和状态管理
  graph/        LangGraph 工作流
  agents/       Planner / Researcher / Analyst / Writer / Critic
  tools/        搜索、抓取、抽取、分类和充分性评估
  infra/        LLM、搜索 Provider、抓取、缓存、数据库和日志
frontend/       Streamlit 前端
scripts/        演示缓存预热和真实 smoke 脚本
tests/          架构、单元、集成和 E2E 测试
docs/           规约、审查记录和修复报告
```

## 快速开始

### 1. 安装 Python

安装 Python 3.12，并确认命令可用：

```bash
python --version
```

如果显示的不是 `3.12.x`，请先切换到 Python 3.12。

### 2. 获取代码

```bash
git clone https://github.com/LAPPLANDQAQ/InsightAgent.git
cd InsightAgent
```

如果已经在本机项目目录中：

```powershell
cd C:\code\InsightAgent
```

### 3. 创建虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS：

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. 安装依赖

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 5. 配置环境变量

复制配置模板：

Windows：

```powershell
Copy-Item .env.example .env
```

Linux / macOS：

```bash
cp .env.example .env
```

打开 `.env`，至少填写 DeepSeek 密钥：

```bash
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的DeepSeek密钥
LLM_HEAVY_MODEL=deepseek-v4-pro
LLM_LIGHT_MODEL=deepseek-v4-flash
LLM_FALLBACK_MODEL=deepseek-v4-flash
```

说明：

- `DEEPSEEK_API_KEY` 不要提交到 Git。
- `TAVILY_API_KEY` 可以留空；留空时系统会跳过 Tavily，使用 DuckDuckGo 作为公开搜索来源。
- `ENFORCE_PROVIDER_MODEL_GUARD=true` 会在启动时校验模型名，建议保持开启。

## 本地运行

启动后端：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

如果 Windows 环境下 `--reload` 触发权限问题，可以去掉 `--reload`：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端地址：

- API 文档：http://127.0.0.1:8000/docs
- OpenAPI：http://127.0.0.1:8000/openapi.json

另开一个终端启动前端：

```bash
streamlit run frontend/streamlit_app.py --server.port=8501 --server.address=127.0.0.1
```

浏览器打开：

```text
http://127.0.0.1:8501
```

如果后端端口不是 8000，可以指定前端访问的 API 地址：

Windows：

```powershell
$env:INSIGHT_API_BASE="http://127.0.0.1:你的端口"
streamlit run frontend/streamlit_app.py --server.port=8501
```

Linux / macOS：

```bash
INSIGHT_API_BASE=http://127.0.0.1:你的端口 streamlit run frontend/streamlit_app.py --server.port=8501
```

## 结果输出

每次任务完成后，前端会输出三类结果：

- 调研文档：直接展示 Markdown 报告，并支持下载为 `.md` 文件。
- 雷达图：基于 `quality_metrics.coverage` 展示各维度证据覆盖情况。
- 质量数据：展示覆盖率、缺失维度、质检问题和运行问题，便于复盘。

## 部署方式

### 方式一：Windows 本地部署

这是 Windows 用户的推荐方式，不需要 Docker。

1. 安装 Python 3.12。
2. 按“快速开始”创建虚拟环境并安装依赖。
3. 复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`。
4. 启动后端：

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. 再开一个 PowerShell 启动前端：

```powershell
streamlit run frontend/streamlit_app.py --server.port=8501 --server.address=127.0.0.1
```

6. 浏览器访问 `http://127.0.0.1:8501`。

### 方式二：Docker Compose 部署

Docker 不是必须的。只有当你的系统已经能正常使用 Docker Desktop，或者你想用容器统一环境时，才需要使用这个方式。

准备 `.env` 后运行：

```bash
docker compose up --build
```

访问：

- 后端：http://127.0.0.1:8000/docs
- 前端：http://127.0.0.1:8501

Docker Compose 会等待 API 健康检查通过后再启动前端。前端容器内部通过 `http://api:8000` 访问后端，本机浏览器仍访问 `http://127.0.0.1:8501`。

停止服务：

```bash
docker compose down
```

## 运行测试

完整验证：

```bash
python -m ruff check app/ tests/ frontend/streamlit_app.py
python -m mypy app/ --ignore-missing-imports
python -m pytest tests/architecture/ tests/unit/ tests/integration/ tests/e2e/ -v
```

## 演示建议

真实联网调研会受到搜索服务、目标网页和 LLM 响应速度影响。面试或演示前可以先预热缓存：

```bash
python scripts/preload_demo_cache.py
```

然后再打开前端创建任务，命中缓存时响应会更稳定。

## API 示例

创建任务：

```bash
curl -X POST http://127.0.0.1:8000/api/tasks -H "Content-Type: application/json" -d "{\"query\":\"AI 编程助手赛道\",\"competitors\":[\"Cursor\",\"GitHub Copilot\"],\"dimensions\":[\"pricing\",\"features\",\"ecosystem\"]}"
```

查询状态：

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}
```

获取报告：

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}/report
```

## 当前限制

- 只处理公开网页，不访问登录后的内容。
- 搜索质量依赖外部搜索 Provider。
- LLM 输出质量受模型稳定性和网页文本质量影响。
- Critic 当前以规则检查为主，LLM Critic 默认关闭。

## 更新日志

### 2026-05-03

- 新增前端调研结果输出：Markdown 文档预览、Markdown 下载、维度证据覆盖雷达图、质量数据面板。
- 修复 Streamlit 前端中文乱码，优化任务状态、输入框和结果展示文案。
- 修复 Writer 兜底报告中文乱码，保证 LLM 调用失败时仍能输出可读报告。
- 统一 DeepSeek 运行时配置，移除旧模型平台相关运行时代码和说明。
- 优化 README 的 Windows 本地部署说明，明确 Docker 为可选部署方式。

## 重要文档

- 执行规约：[docs/InsightAgent_Codex执行规约_v6_审查修复版.md](docs/InsightAgent_Codex执行规约_v6_审查修复版.md)
- 首次修复报告：[docs/first_issue_fix_report_2026-05-03.md](docs/first_issue_fix_report_2026-05-03.md)
- 历史审查问题：[docs/issues_found_2026-05-02.md](docs/issues_found_2026-05-02.md)
