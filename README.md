# InsightAgent

InsightAgent 是一个面向竞品调研的多 Agent 分析系统。用户输入赛道、竞品或分析维度后，系统会自动规划调研、搜索公开资料、抓取网页、抽取证据、生成分析结论，并输出带证据引用的 Markdown 报告。

## 项目亮点

- 多 Agent 协作：Planner、Researcher、Analyst、Writer、Critic 分工明确。
- 证据驱动：搜索、抓取、抽取结果进入结构化证据模型，报告结论引用 `evidence_id`。
- LangGraph 工作流：使用 `StateGraph` 组织调研、充分性检查、分析、写作和质检节点。
- 千问运行时守卫：业务 LLM 只允许 Qwen/QwQ 系列模型，真实模型名集中在配置层。
- 稳定性设计：搜索、抓取、抽取均支持缓存；抓取失败短缓存；服务重启后会处理僵死任务。
- 可验证边界：架构测试限制跨层导入、外部 SDK 使用、文件大小、公共函数 docstring。
- 前后端完整：FastAPI 提供任务接口，Streamlit 提供可视化操作界面。

## 技术栈

- Python 3.12
- FastAPI
- LangGraph
- Pydantic v2
- SQLAlchemy 2.x
- Streamlit
- HTTPX
- DashScope OpenAI-compatible Qwen API
- SQLite cache / SQLite task DB

## 架构

```text
api -> services -> graph -> agents -> tools -> infra
```

关键约束：

- `agents/` 不直接导入外部 SDK，也不导入 infra 实现类。
- OpenAI SDK 只允许在 `app/infra/llm/qwen_dashscope_client.py` 中作为 DashScope 兼容传输层使用。
- 业务代码只使用 `model_role`，不硬编码真实模型名。
- `tools/` 之间不互相调用，`app.tools.dedup` 纯函数除外。

## 目录结构

```text
app/
  api/          FastAPI 路由
  services/     任务编排、状态管理
  graph/        LangGraph 工作流
  agents/       Planner / Researcher / Analyst / Writer / Critic
  tools/        搜索、抓取、抽取、分类、充分性评估
  infra/        LLM、搜索 Provider、抓取、缓存、数据库、日志
frontend/       Streamlit 前端
scripts/        演示预热和真实烟测脚本
tests/          架构、单元、集成、E2E 测试
docs/           规约、审查记录、修复报告
```

## 快速开始

### 1. 安装 Python

安装 Python 3.12，并确认命令可用：

```bash
python --version
```

如果显示的不是 `3.12.x`，请先切换 Python 版本。

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

打开 `.env`，至少配置：

```bash
DASHSCOPE_API_KEY=你的千问DashScope密钥
LLM_HEAVY_MODEL=qwen-max
LLM_LIGHT_MODEL=qwen-turbo
LLM_FALLBACK_MODEL=qwen-plus
```

说明：

- `TAVILY_API_KEY` 可留空，系统会跳过 Tavily，使用 DuckDuckGo。
- `.env` 包含密钥，不要提交到 Git。
- 业务运行时不要把模型改成 GPT、Claude、DeepSeek 等非千问模型。

## 本地运行

启动后端：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
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

如果后端端口不是 8000，可设置：

Windows：

```powershell
$env:INSIGHT_API_BASE="http://127.0.0.1:你的端口"
streamlit run frontend/streamlit_app.py --server.port=8501
```

Linux / macOS：

```bash
INSIGHT_API_BASE=http://127.0.0.1:你的端口 streamlit run frontend/streamlit_app.py --server.port=8501
```

## Docker 部署

准备 `.env` 后运行：

```bash
docker compose up --build
```

访问：

- 后端：http://127.0.0.1:8000/docs
- 前端：http://127.0.0.1:8501

Docker Compose 会等待 API 健康检查通过后再启动前端。前端容器内部会通过 `http://api:8000` 访问后端，本机浏览器仍访问 `http://127.0.0.1:8501`。

停止服务：

```bash
docker compose down
```

## 运行测试

完整验证：

```bash
python -m pytest tests/architecture/ tests/unit/ tests/integration/ tests/e2e/ -v
python -m ruff check app/ tests/ frontend/streamlit_app.py
python -m mypy app/ --ignore-missing-imports
```

当前修复后验证结果：

```text
51 passed
ruff: All checks passed
mypy: Success: no issues found
```

## 演示建议

真实联网调研会受到搜索服务、目标网页和 LLM 响应速度影响。面试或演示前建议先预热缓存：

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

- 只处理公开网页，不访问登录后内容。
- 搜索质量依赖外部搜索 Provider。
- LLM 输出质量受模型稳定性和网页文本质量影响。
- Critic 当前以规则检查为主，LLM Critic 默认关闭。

## 重要文档

- 执行规约：[docs/InsightAgent_Codex执行规约_v6_审查修复版.md](docs/InsightAgent_Codex执行规约_v6_审查修复版.md)
- 首次修复报告：[docs/first_issue_fix_report_2026-05-03.md](docs/first_issue_fix_report_2026-05-03.md)
- 历史审查问题：[docs/issues_found_2026-05-02.md](docs/issues_found_2026-05-02.md)
