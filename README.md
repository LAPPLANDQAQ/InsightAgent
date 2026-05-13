# InsightAgent v4.0.2

InsightAgent 是一个基于 AI 的本地竞品分析智能体（Agent），可自动完成市场调研、证据收集、维度分析和报告撰写。稳定版运行时采用 **FastAPI + LangGraph + Streamlit + SQLite + DeepSeek** 技术栈，通过 OpenAI 兼容协议访问 DeepSeek 模型。

## 项目概览

InsightAgent 的核心能力是接收用户输入的市场或产品领域，自动规划分析维度、搜索公开网页信息、提取结构化证据，并生成包含引用支持的竞品分析报告。

### 核心特性

- **全自动分析流水线**：Plan → Research → Analyze → Write → Critique，一气呵成
- **多竞品对比**：支持同时分析多个竞品，自动发现或用户指定
- **多维度评估**：支持定价、功能、生态、市场份额等自定义分析维度
- **证据溯源**：每条分析结论均附带网页来源引用和证据 ID
- **质量控制**：内置 Critic 审查环节，自动检测缺失维度、无效引用等问题
- **中英文界面**：Streamlit 前端支持中文/英文双语切换
- **离线测试**：全套测试使用 Fake/Stub，无需真实 API 密钥

### 稳定版范围

| 组件 | 稳定版方案 | 说明 |
|------|-----------|------|
| LLM 运行时 | DeepSeek only | 仅支持 deepseek-v4-pro / deepseek-v4-flash / deepseek-chat / deepseek-reasoner |
| 数据库 | SQLite | 默认存储于 `./data` 目录 |
| 缓存 | SQLite / Memory | 通过 `CACHE_BACKEND` 配置切换 |
| 前端 | Streamlit | 运行于 8501 端口 |
| 搜索 | Tavily + DuckDuckGo | 通过 `SEARCH_PROVIDERS` 配置 |
| 默认工作流 | Planner → Researcher → Analyst → Writer → Critic | 5 阶段流水线 |
| RAG 检索增强 | 可选（默认关闭） | `ENABLE_RAG_RESEARCH=true` 启用 |
| Harness / MCP | 归档/实验性 | 稳定版默认禁用 |

### 代码分层架构

```text
api（接口层）→ services（服务层）→ graph（工作流）→ agents（智能体）→ tools/rag/harness（工具）→ infra（基础设施）
```

- **Agent 层**：仅负责编排，不直接调用 SDK、HTTP、数据库或文件系统
- **Tools 层**：封装外部调用（搜索、网页抓取、LLM 提取）
- **Infra 层**：提供 LLM 客户端、HTTP 客户端、缓存、数据库等基础能力
- **Services 层**：任务生命周期管理、状态追踪、报告持久化

### v4.0.2 关键修复清单

| 修复项 | 说明 |
|--------|------|
| 引擎释放 | FastAPI 关闭时自动 dispose SQLAlchemy engine |
| LLM 客户端关闭 | DeepSeekClient 新增 aclose() 资源释放方法 |
| 容器资源清理 | Container.aclose() 同时关闭 LLM 和 Fetch 客户端 |
| 版本号显示 | 前端侧边栏版本号修正为 v4.0.2 |
| 中文翻译 | 修复残留的英文占位翻译为真实中文 |
| Docker 文档 | 补充 Docker Compose 就绪检查说明 |
| API 状态码 | POST /api/tasks 创建成功返回 201 |
| 取消响应对齐 | 取消任务 API 返回 FAILED 状态与实际持久化状态一致 |
| Critic 中文前缀 | 支持全角冒号中文元数据前缀（竞品：/ 维度：/ 证据：） |
| 前端错误展示 | 前端异常信息不再直接暴露原始错误，改为友好提示 |
| CI 工作流 | Demo smoke 重命名为 Preview demo smoke，添加注释说明 |

## 环境要求

- **Python**：3.12（必须，不支持 3.11 及以下，不支持 3.13）
- **操作系统**：Windows / macOS / Linux
- **可选**：Docker（用于容器化部署）

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd InsightAgent
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. 安装依赖

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. 配置环境变量

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

编辑 `.env` 文件，设置 `DEEPSEEK_API_KEY` 为你的 DeepSeek API 密钥。其他配置项使用默认值即可运行。

> **注意**：测试套件使用 Fake/Stub，无需真实 API 密钥。仅实际运行任务时需要有效的 DeepSeek API Key。

### 5. 启动 API 服务

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证服务状态：

```bash
curl http://127.0.0.1:8000/healthz   # 存活检查
curl http://127.0.0.1:8000/readyz    # 就绪检查（含 DB/缓存/LLM 配置状态）
```

### 6. 启动 Streamlit 前端

```bash
streamlit run frontend/streamlit_app.py --server.port=8501 --server.address=127.0.0.1
```

浏览器访问 `http://127.0.0.1:8501` 即可使用。

> 前端默认连接 `http://127.0.0.1:8000`。如需更改后端地址，设置环境变量 `INSIGHT_API_BASE`。

## API 接口

### 创建分析任务

```bash
curl -X POST http://127.0.0.1:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI 编程助手市场",
    "competitors": ["Cursor", "GitHub Copilot", "Windsurf"],
    "dimensions": ["定价", "功能", "生态系统", "市场份额"]
  }'
```

返回 `201 Created`：

```json
{"task_id": "task_a1b2c3d4e5f6", "status": "PENDING"}
```

### 查询任务状态

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}
```

返回实时状态、当前阶段、进度百分比、预估剩余时间、问题列表等信息。

### 取消运行中的任务

```bash
curl -X DELETE http://127.0.0.1:8000/api/tasks/{task_id}
```

返回 `202 Accepted`。

### 获取分析报告

```bash
curl http://127.0.0.1:8000/api/tasks/{task_id}/report
```

返回 Markdown 格式的分析报告和质量指标。

### 接口汇总

| 方法 | 路径 | 说明 | 成功状态码 |
|------|------|------|-----------|
| POST | `/api/tasks` | 创建分析任务 | 201 |
| GET | `/api/tasks/{id}` | 查询任务状态 | 200 |
| DELETE | `/api/tasks/{id}` | 取消任务 | 202 |
| GET | `/api/tasks/{id}/report` | 获取报告 | 200 |
| GET | `/healthz` | 存活探针 | 200 |
| GET | `/readyz` | 就绪探针 | 200 / 503 |

## 工作流说明

### 默认流水线阶段

```
Queued → Planner → Researcher → Analyst → Writer → Critic → Completed
```

1. **Planner（规划器）**：分析用户查询，确定竞品列表和分析维度
2. **Researcher（研究员）**：搜索公开网页，提取结构化证据
3. **Analyst（分析师）**：对证据进行维度分析，生成对比洞察
4. **Writer（撰写器）**：生成 Markdown 格式的分析报告
5. **Critic（审查器）**：规则化质量检查，检测缺失维度、无效引用等问题

### 并发控制

- LLM 重试/回退：支持 transient error 自动重试，主模型失败后回退到 fallback 模型
- 信号量并发限制：heavy 模型（默认 2 并发）、light 模型（默认 5 并发）
- 任务超时：默认 900 秒，可通过 `TASK_TIMEOUT_SECONDS` 配置
- 队列限制：通过 `MAX_QUEUED_TASKS` 控制待处理任务上限

## 配置说明

完整配置项参见 `.env.example`，以下为关键配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DEEPSEEK_API_KEY` | - | **必填**，DeepSeek API 密钥 |
| `LLM_HEAVY_MODEL` | deepseek-v4-pro | 重度推理模型（规划、分析、撰写） |
| `LLM_LIGHT_MODEL` | deepseek-v4-flash | 轻量模型（提取、分类） |
| `LLM_FALLBACK_MODEL` | deepseek-v4-flash | 回退模型 |
| `CACHE_BACKEND` | sqlite | 缓存后端（sqlite / memory） |
| `DB_URL` | sqlite:///./data/insight.db | 数据库连接地址 |
| `SEARCH_PROVIDERS` | tavily,duckduckgo | 搜索提供商 |
| `MAX_CONCURRENT_TASKS` | 2 | 最大并发任务数 |
| `TASK_TIMEOUT_SECONDS` | 900 | 单任务超时时间（秒） |
| `SUFFICIENCY_THRESHOLD` | 0.6 | 证据充分性阈值 |
| `ENABLE_LLM_CRITIC` | false | 启用 LLM 增强审查 |
| `ENABLE_RAG_RESEARCH` | false | 启用 RAG 检索增强 |

## Docker 部署

### 构建与启动

```bash
docker compose build
docker compose up
```

### 注意事项

- Docker Compose 使用 `/readyz` 作为 API 健康检查端点
- 启动前必须将 `.env.example` 复制为 `.env` 并设置有效的 `DEEPSEEK_API_KEY`
- 若未配置有效的 API Key，API 服务将无法通过就绪检查，前端将等待
- Docker 构建为可选项，应与本地 Python 验证分开报告

## 验证与测试

### 本地代码检查

```bash
python -m compileall app frontend          # 编译检查
python -m ruff check app tests examples scripts frontend   # 代码规范
python -m mypy app --ignore-missing-imports                 # 类型检查
python -m pytest tests -q                                   # 运行测试
```

### 当前验证状态（v4.0.2 Finalization）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| compileall | PASS | app + frontend 全部编译通过 |
| ruff | PASS | 零错误 |
| mypy | PASS | 123 个源文件无类型错误 |
| pytest | PASS | 225 个测试全部通过 |
| Docker build | 未运行 | Docker 不可用 |
| Docker up | 未运行 | Docker 不可用 |
| Streamlit 手动检查 | 未运行 | 需要交互式浏览器 |

## 测试策略

- **单元测试**：测试 Agent、Tool、Schema、LLM 客户端、前端辅助函数等独立模块
- **集成测试**：测试 API 稳定性、工作流编排、Feature Flag 控制
- **架构测试**：测试分层导入规则、文件大小限制、运行时模型守卫
- **评估测试**：测试 RAG 检索质量、引用有效性、报告质量等指标

所有测试使用 Fake/Stub/Mock，不依赖真实的 LLM API、搜索 API、网页请求或 Docker 环境。

## 目标指标

以下为设计目标指标，非实测值。在获得可信的评估结果之前，实测值保持 `TBD`。

| 指标 | 目标值 | 实测值 |
|------|--------|--------|
| RAG Hit@5 | >= 0.90 | TBD |
| MRR | >= 0.85 | TBD |
| 引用有效性 | >= 95% | TBD |
| 维度覆盖率 | >= 90% | TBD |
| 任务完成率 | >= 95% | TBD |

## 安全与架构约束

- **DeepSeek-only 运行时**：`ENFORCE_PROVIDER_MODEL_GUARD=true` 确保只允许 DeepSeek 模型
- **OpenAI SDK**：仅作为 DeepSeek OpenAI 兼容协议的传输层
- **SSRF 防护**：HTTP 抓取客户端阻止私有/本地地址
- **密钥脱敏**：错误日志和输出中自动脱敏 API Key 和 Token
- **Agent 编排限制**：Agent 不得直接调用 SDK、HTTP、数据库或文件系统

## 项目结构

```text
InsightAgent/
├── app/                    # 后端核心代码
│   ├── agents/             # 智能体（Planner, Researcher, Analyst, Writer, Critic）
│   ├── api/                # FastAPI 路由（tasks, health）
│   ├── graph/              # LangGraph 工作流定义
│   ├── infra/              # 基础设施（LLM, Cache, DB, Fetch, Search, Security）
│   ├── rag/                # RAG 检索增强模块
│   ├── harness/            # 实验性 Harness 模块
│   ├── mcp_server/         # 实验性 MCP 服务
│   ├── schemas/            # Pydantic 数据模型
│   ├── services/           # 业务服务层
│   ├── tools/              # 工具层（搜索、抓取、提取、分类）
│   ├── config.py           # 全局配置
│   ├── container.py        # DI 容器
│   └── main.py             # FastAPI 应用入口
├── frontend/               # Streamlit 前端
│   ├── components/         # UI 组件（任务表单、状态面板、报告查看器）
│   ├── streamlit_app.py    # 主入口
│   ├── utils.py            # 工具函数
│   ├── i18n.py             # 中英文翻译
│   └── theme.py            # CSS 主题
├── tests/                  # 测试套件
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   ├── architecture/       # 架构约束测试
│   ├── evaluation/         # 评估测试
│   ├── harness/            # Harness 测试
│   ├── mcp/                # MCP 测试
│   └── fixtures/           # 测试夹具
├── docs/                   # 文档
├── examples/               # 示例脚本
├── scripts/                # 工具脚本
├── pyproject.toml          # 项目配置
├── Dockerfile              # Docker 镜像
├── docker-compose.yml      # Docker Compose 编排
├── .env.example            # 环境变量模板
└── README.md               # 本文件
```

## 相关文档

- [文档索引](docs/README.md)
- [架构设计](docs/architecture.md)
- [运行时说明](docs/runtime.md)
- [RAG 模块](docs/rag.md)
- [待办项](docs/deferred.md)

## 许可证

本项目仅用于学习和展示目的。
