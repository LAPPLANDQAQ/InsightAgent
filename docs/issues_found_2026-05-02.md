# InsightAgent 审查问题清单

日期：2026-05-02

本文档列出对项目进行全面审查后发现的所有问题，包含精确的文件路径、行号和修复方案，可供后续开发直接执行。

---

## P0 — 阻塞性问题

### P0-1 Dockerfile `pip install -e .` 在源码复制前执行

- **文件**: `Dockerfile`
- **行号**: 3-5
- **现象**: `pip install -e .`（editable 模式）需要包源码目录 `app/` 存在才能创建可编辑链接，但 `COPY app ./app` 在 `RUN pip install` 之后执行。构建会因找不到包目录而失败。
- **同时也缺失** `[build-system]` 声明（`pyproject.toml` 中无此节），依赖 pip 的隐式默认行为。

**修复方案**:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY frontend ./frontend
COPY scripts ./scripts
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

即将源码 COPY 移到 pip install 之前。如果需要利用 Docker 层缓存，可改为 `pip install .`（非 editable）并在 pyproject.toml 中补上 `[build-system]`。

---

## P1 — 高优先级

### P1-1 `datetime.utcnow()` 已弃用 (8 处)

Python 3.12 中 `datetime.utcnow()` 标记为弃用，应统一替换为 `datetime.now(datetime.UTC)`。部分代码已经用了新写法（`app/agents/researcher.py:92`、`app/infra/logger.py:22`），其余位置未跟进。

**修复清单**:

| 文件 | 行号 | 当前代码 | 替换为 |
|------|------|----------|--------|
| `app/services/task_service.py` | 142 | `datetime.utcnow()` | `datetime.now(UTC)` |
| `app/services/task_service.py` | 143 | `datetime.utcnow()` | `datetime.now(UTC)` |
| `app/services/task_service.py` | 187 | `datetime.utcnow()` | `datetime.now(UTC)` |
| `app/services/task_service.py` | 203 | `datetime.utcnow()` | `datetime.now(UTC)` |
| `app/infra/db/models.py` | 23 | `default=datetime.utcnow` | `default=lambda: datetime.now(UTC)` |
| `app/infra/db/models.py` | 24 | `default=datetime.utcnow` | `default=lambda: datetime.now(UTC)` |
| `app/infra/db/models.py` | 75 | `default=datetime.utcnow` | `default=lambda: datetime.now(UTC)` |
| `app/infra/db/repository.py` | 41 | `datetime.utcnow()` | `datetime.now(UTC)` |

**注意**: `task_service.py` 第 1 行 `from datetime import datetime` 需改为 `from datetime import UTC, datetime`。`models.py` 第 3 行需加 `from datetime import UTC`。`repository.py` 第 4 行需改为 `from datetime import UTC, datetime`。

### P1-2 DateTime 列缺少 timezone=True

- **文件**: `app/infra/db/models.py`
- **行号**: 23-25, 75
- **现象**: `created_at`, `updated_at`, `finished_at`（Task 表）和 `created_at`（Report 表）均使用 `DateTime` 无 `timezone=True`。一旦改为 `datetime.now(UTC)`（时区感知），naive DateTime 列会丢失时区信息或写入失败（取决于 SQLAlchemy 配置和数据库驱动）。

**修复**: 所有 `DateTime` 改为 `DateTime(timezone=True)`:

```python
# Task 表 (行 23-25)
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# Report 表 (行 75)
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

---

## P2 — 中优先级

### P2-1 Mypy: `RunnableAgent` Protocol 缺少 `name` 属性

- **文件**: `app/graph/workflow.py`
- **行号**: 10-15 (Protocol 定义), 47 (使用 `agent.name`)
- **现象**: `InsightWorkflow.ainvoke` 在 line 47 调用 `agent.name`，但 `RunnableAgent` Protocol 只声明了 `run()` 方法，未声明 `name`。所有实际 Agent 继承自 `AgentBase`（有 `name` 类属性），但协议层面不一致。

**修复**: 在 `RunnableAgent` Protocol 中添加 `name`:

```python
class RunnableAgent(Protocol):
    """Protocol for workflow agents."""
    name: str

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the agent and return state updates."""
        ...
```

### P2-2 Mypy: `LLMClient.invoke` 返回联合类型 `T | str` 导致窄化失败 (4 处)

- **文件与行号**:
  - `app/agents/planner.py:48,51` — `plan.model_dump()` 和 `plan.competitors`
  - `app/agents/analyst.py:48` — `analysis.model_dump()`
  - `app/tools/extraction_tool.py:68` — `result.evidences`
- **根因**: `LLMClient.invoke` 声明返回 `T | str`。即使调用方传入 `schema=SomeModel`（运行时永远返回 `T`，不会返回 `str`），mypy 也无法通过类型窄化排除 `str` 分支。

**修复方案（选其一）**:

方案 A（推荐，改动最小）—— 在调用点加 `assert not isinstance(plan, str)`:

```python
plan = await self.llm.invoke(prompt=prompt, model_role="heavy", schema=ResearchPlan, ...)
assert not isinstance(plan, str)  # schema is provided, so str is impossible
```

方案 B（架构级改动）—— 将 `invoke` 拆成两个重载：`invoke_text(...) -> str` 和 `invoke_structured(...) -> T`。

### P2-3 Mypy: `Critic._issue` 参数类型过宽

- **文件**: `app/agents/critic.py`
- **行号**: 62-69（方法定义）, 64, 66（调用点）
- **根因**: `_issue` 参数声明为 `issue_type: str, target_stage: str`，但 `CriticIssue` schema（`app/schemas/critic.py:11,21`）要求 `Literal['missing_evidence', 'invalid_evidence_ref', ...]` 和 `Literal['researcher', 'analyst', 'writer']`。mypy 无法将 `str` 赋值给 `Literal`。

**修复**: 为 `_issue` 参数加上精确的类型别名:

```python
from app.schemas.critic import CriticIssue

IssueType = Literal["missing_evidence", "invalid_evidence_ref", "dimension_missing",
                     "unsupported_claim", "weak_source", "format_error", "logic_gap"]
TargetStage = Literal["researcher", "analyst", "writer"]

@staticmethod
def _issue(issue_type: IssueType, target_stage: TargetStage, message: str) -> CriticIssue:
    ...
```

### P2-4 Mypy: `Container._search_providers` 列表类型推断错误

- **文件**: `app/container.py`
- **行号**: 61-71
- **根因**: 空列表先 append `TavilyProvider`，mypy 推断为 `list[TavilyProvider]`，后续 `append(DuckDuckGoProvider)` 类型不匹配。

**修复**: 显式声明列表类型:

```python
def _search_providers(self) -> list[object]:
    providers: list[object] = []
    ...
```

或者使用 `SearchProvider` Protocol 作为类型（如果给 search.py 的 `SearchProvider` 加上 `@runtime_checkable`）。

### P2-5 Schema 与 DB Model 字段长度不一致

- **文件**: `app/schemas/evidence.py:13` vs `app/infra/db/models.py:56`
- **字段**: `EvidenceItem.claim`
- **Schema**: `Field(max_length=80)`
- **DB**: `String(160)`

DB 允许存更长的字符串，但 Pydantic 校验在 80 字符时就拦截。两者应统一。建议统一为 160，因为用户可见的 claim 摘要 80 字符可能不够。

---

## P3 — 低优先级

### P3-1 死代码: `ReportService`

- **文件**: `app/services/report_service.py`
- **说明**: 只有一个 `normalize_markdown` 方法（返回 `markdown.strip()`），整个项目无任何 import 或使用。
- **处理**: 直接删除此文件及其在包的引用。

### P3-2 死代码: `MetricService`

- **文件**: `app/services/metric_service.py`
- **说明**: 只有一个 `evidence_count` 方法，整个项目无任何 import 或使用。
- **处理**: 直接删除此文件。

### P3-3 死代码: `TaskRepository`

- **文件**: `app/infra/db/repository.py`
- **说明**: `TaskService` 直接使用 SQLAlchemy Session 操作数据库，不经过 Repository。此外 `set_status` 方法也用了已弃用的 `datetime.utcnow()`。
- **处理**: 删除此文件。如果将来需要 Repository 模式，届时再写。

### P3-4 重复的去重逻辑

- **文件**: `app/infra/search/service.py:91-99` 与 `app/tools/dedup.py:31-48`
- **说明**: `SearchService._dedupe` 只做 `rstrip("/") + lower()`；`dedupe_search_results` 做完整规范化（去除 tracking params、fragment 等）。两个函数都负责去重但行为不同。
- **处理**: 删掉 `SearchService._dedupe`（只保留缓存用途的 key），让去重统一走 `app/tools/dedup.dedupe_search_results`。或者反过来，让 `SearchService._dedupe` 也调用 `normalize_url`。

### P3-5 `merge_state` 的隐式契约

- **文件**: `app/graph/reducers.py:17-18`
- **问题**: 当 `update` 包含 `issues` 时直接**替换**，不追加。每个 Agent 必须在写入 `issues` 前手动从 `state` 读取并继承。如果新 Agent 只写 `issues: ["err"]` 而不读 `state.get("issues")`，历史 issues 静默丢失。
- **处理**: 改为真正的 merge 语义：

```python
if "issues" in state or "issues" in update:
    merged["issues"] = list(state.get("issues", [])) + list(update.get("issues", []))
```

同时修改各 Agent 中 `issues = [*state.get("issues", []), ...]` 为 `issues = [...]`（不再需要手动继承）。

### P3-6 任务状态仅存内存，服务重启后丢失

- **文件**: `app/services/task_service.py:44` — `self._tasks: dict[str, dict] = {}`
- **问题**: 重启后所有进行中任务状态消失。`get_status` 回退到数据库查询，但数据库中 `RUNNING` 状态的任务会永远卡住，没有任何恢复机制。
- **处理**: 在 `get_status` 中，如果数据库查询到的 task 状态是 `RUNNING` 但内存中不存在，应返回 `FAILED` 状态并附带说明信息，或者启动时清理数据库中僵死的 `RUNNING` 状态。

### P3-7 Streamlit 硬编码 API_BASE

- **文件**: `frontend/streamlit_app.py:9`
- **当前**: `API_BASE = "http://127.0.0.1:8000"`
- **处理**: 改为读取环境变量：

```python
import os
API_BASE = os.getenv("INSIGHT_API_BASE", "http://127.0.0.1:8000")
```

---

## P4 — 改善建议

### P4-1 测试覆盖不足

- **文件**: `tests/unit/test_task_service.py`
- **现状**: 仅 1 个测试（`test_persist_accepts_evidence_payload_with_task_id`）
- **缺失的测试用例**:

| 方法 | 需覆盖场景 |
|------|-----------|
| `create_task` | 正常创建、带/不带 competitors 和 dimensions |
| `_run_task` | 正常完成、工作流抛异常 |
| `get_status` | 内存命中 RUNNING、内存命中 COMPLETED、DB 回退、NOT_FOUND |
| `get_report` | 存在报告、不存在报告返回 None |
| `_mark_failed` | 验证 DB 中 error_message 和 status 被正确更新 |
| `_estimate_remaining_seconds` | 已完成(return 0)、progress≤0.05(return 120)、正常计算 |
| `_on_workflow_stage` | 验证 progress 计算正确、task_id 为空时安全返回 |

### P4-2 Streamlit 每次轮询创建新 httpx.Client

- **文件**: `frontend/streamlit_app.py:104,122,137`
- **现象**: `_create_task`、`_get_status`、`_get_report` 各自 `with httpx.Client(timeout=20.0)`。轮询间隔 2 秒，每次轮询都做 TCP 三次握手。
- **处理**: 提取为模块级 `httpx.Client` 实例，复用连接池：

```python
_http = httpx.Client(timeout=20.0, limits=httpx.Limits(max_keepalive_connections=5))

def _create_task(...):
    response = _http.post(...)
```

### P4-3 docker-compose 缺少 healthcheck 等待

- **文件**: `docker-compose.yml:15-16`
- **现象**: `depends_on: api` 只等容器启动，不等 API 就绪。前端可能在后端完成初始化前就开始处理请求。
- **处理**: 给 api 服务添加 healthcheck，frontend 使用 `depends_on` 的 `condition: service_healthy`。

### P4-4 文档 dangling 引用

- **文件**: `docs/spec.md:5`
- **现象**: 引用 `InsightAgent_Codex执行规约_v6_审查修复版.md`，但该文件在仓库中不存在。
- **处理**: 将规约文件放入仓库，或删除/更新 spec.md 的引用。

### P4-5 `task_service.py` 行数逼近上限

- **文件**: `app/services/task_service.py`
- **当前行数**: 296 行
- **架构测试上限**: `tests/architecture/test_file_size_limits.py` 中 `MAX_LINES = 300`
- **处理**: 可将 `_status_payload` 和 `_estimate_remaining_seconds` 提取到单独的 helper 模块，或将 `STAGE_LABELS` 移到配置层。

### P4-6 httpx 抓取无重试机制

- **文件**: `app/infra/fetch/httpx_client.py:51-78`
- **现象**: `_fetch_uncached` 新建 `AsyncClient` 但无重试。项目已依赖 `tenacity`（见 `pyproject.toml`），但未使用。
- **处理**: 对 `_fetch_uncached` 中的 `client.get(url)` 加 `@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))`。

---

## 修复顺序建议

```
第一轮（安全与可用性）:
  P0-1 → P1-1 → P1-2

第二轮（类型安全）:
  P2-1 → P2-2 → P2-3 → P2-4

第三轮（清理与一致性）:
  P3-1 → P3-2 → P3-3 → P3-4 → P3-5 → P2-5

第四轮（体验优化）:
  P3-6 → P3-7 → P4-1 → P4-2 → P4-3 → P4-4 → P4-5 → P4-6
```

每轮完成后运行 `python -m pytest tests/ -v && python -m ruff check app/ tests/ && python -m mypy app/ --ignore-missing-imports` 确保不引入回归。
