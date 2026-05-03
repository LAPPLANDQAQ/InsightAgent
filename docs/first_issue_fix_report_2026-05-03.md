# 第一次问题修复及解决方案

日期：2026-05-03

## 修复范围

本次修复基于 `docs/issues_found_2026-05-02.md` 和再次全面审查结果，优先处理可运行性、规约合规、类型安全、运行健壮性和部署体验问题。

## 已修复问题

### 1. Docker 构建失败

问题：`Dockerfile` 在复制 `app/` 源码前执行 `pip install -e .`，editable 安装会找不到包目录。

解决方案：

- 将 `COPY app ./app`、`COPY frontend ./frontend`、`COPY scripts ./scripts` 移到安装命令前。
- 在 `pyproject.toml` 补充 `[build-system]`，避免依赖 pip 隐式默认行为。

涉及文件：

- `Dockerfile`
- `pyproject.toml`

### 2. Docker Compose 前端无法访问后端

问题：Streamlit 硬编码 `http://127.0.0.1:8000`，容器内访问的是前端容器自身，不是 API 容器。

解决方案：

- 前端改为读取 `INSIGHT_API_BASE`。
- Compose 中为前端设置 `INSIGHT_API_BASE=http://api:8000`。
- 为 API 增加 healthcheck，前端等待 API 健康后启动。

涉及文件：

- `frontend/streamlit_app.py`
- `docker-compose.yml`

### 3. 工作流未使用 LangGraph

问题：原实现是自写顺序执行器，未体现规约要求的 LangGraph 节点和条件路由。

解决方案：

- 使用 `StateGraph` 构建工作流。
- 增加 `sufficiency_check`、`route_after_sufficiency`、`route_after_critic`、`finalize`。
- 保留 `ainvoke` 调用接口，避免影响 TaskService 和测试。

涉及文件：

- `app/graph/workflow.py`
- `app/graph/reducers.py`
- `app/graph/state.py`

### 4. Mypy 类型错误

问题：`RunnableAgent` 缺少 `name`，结构化 LLM 返回值为 `T | str`，Critic Literal 类型过宽，Container provider 列表推断错误。

解决方案：

- 为 `RunnableAgent` Protocol 声明 `name`。
- 对结构化 LLM 调用结果增加类型断言。
- 为 Critic issue 类型增加 Literal 类型别名。
- 为搜索 Provider 列表显式声明 `list[SearchProvider]`。

涉及文件：

- `app/graph/workflow.py`
- `app/agents/planner.py`
- `app/agents/analyst.py`
- `app/tools/extraction_tool.py`
- `app/agents/critic.py`
- `app/container.py`

### 5. `datetime.utcnow()` 和时区问题

问题：Python 3.12 已弃用 `datetime.utcnow()`，数据库时间列未声明时区。

解决方案：

- 统一改为 `datetime.now(UTC)`。
- 将 ORM 时间列改为 `DateTime(timezone=True)`。

涉及文件：

- `app/services/task_service.py`
- `app/infra/db/models.py`

### 6. 服务重启后 RUNNING 任务卡死

问题：任务运行状态主要保存在内存，服务重启后 DB 中的 `RUNNING` 任务无法恢复也不会失败。

解决方案：

- TaskService 初始化时清理 DB 中僵死的 `RUNNING` 任务。
- `get_status` 发现 DB 中仍为 `RUNNING` 且内存无执行上下文时，标记为 `FAILED` 并返回说明。
- 新增回归测试覆盖该场景。

涉及文件：

- `app/services/task_service.py`
- `app/services/task_status.py`
- `tests/unit/test_task_service.py`

### 7. 抓取层缺少安全防护和重试

问题：抓取任意 URL 存在 SSRF 风险，且没有响应体大小限制、内容类型检查和重试。

解决方案：

- 限制 URL scheme 为 `http/https`。
- 拦截 localhost、私网 IP、保留地址、链路本地地址等。
- 真实网络请求前解析 DNS，避免域名解析到私网地址。
- 限制最大响应体大小为 2 MB。
- 检查内容类型，只处理文本和 HTML 类响应。
- 使用 tenacity 对 HTTPX 网络异常做 2 次重试。
- 新增 localhost 拦截测试。

涉及文件：

- `app/infra/fetch/httpx_client.py`
- `tests/unit/test_search_fetch.py`

### 8. 抽取工具未缓存，且调用方截断输入

问题：规约要求 extract 结果经过缓存，且输入超过 2000 字时直接抛错；原 Researcher 调用时使用 `text[:2000]` 截断。

解决方案：

- ExtractionTool 增加可选缓存，缓存 key 包含竞品、维度、来源 URL、文本 hash 和最大证据数量。
- 命中缓存时会按当前 task/source 信息重写 Evidence 字段，避免跨任务污染。
- Researcher 不再截断文本，超过长度由 ExtractionTool 拒绝。
- 抽取失败会记录 issue，再生成低置信度 fallback evidence。
- 新增抽取缓存回归测试。

涉及文件：

- `app/tools/extraction_tool.py`
- `app/agents/researcher.py`
- `app/container.py`
- `tests/unit/tools/test_tools.py`

### 9. issues 合并语义不可靠

问题：`merge_state` 对 `issues` 直接替换，新 Agent 如果只返回新增 issue 会丢失历史问题。

解决方案：

- `merge_state` 改为追加语义。
- Planner、Analyst、Writer、Researcher、Critic 只返回本阶段新增 issues。

涉及文件：

- `app/graph/reducers.py`
- `app/agents/planner.py`
- `app/agents/analyst.py`
- `app/agents/writer.py`
- `app/agents/researcher.py`
- `app/agents/critic.py`

### 10. 清理死代码和文档引用

问题：存在未使用的 `ReportService`、`MetricService`、`TaskRepository`；`docs/spec.md` 指向仓库根目录中不存在的规约文件。

解决方案：

- 删除未使用服务和仓储文件。
- 更新 `docs/spec.md`，指向 `docs/InsightAgent_Codex执行规约_v6_审查修复版.md`。

涉及文件：

- `app/services/report_service.py`
- `app/services/metric_service.py`
- `app/infra/db/repository.py`
- `docs/spec.md`

### 11. README 信息过多且重点不突出

问题：旧 README 内容偏长，面试官和使用者不容易快速抓住项目亮点和部署路径。

解决方案：

- 重写 README。
- 保留并优化本地部署、Docker 部署、测试验证、演示建议。
- 突出多 Agent、LangGraph、证据链、DeepSeek守卫、缓存和架构测试等亮点。

涉及文件：

- `README.md`

## 验证结果

已执行：

```powershell
python -m pytest tests/architecture/ tests/unit/ tests/integration/ tests/e2e/ -v
python -m ruff check app/ tests/ frontend/streamlit_app.py
python -m mypy app/ --ignore-missing-imports
```

结果：

```text
51 passed
ruff: All checks passed
mypy: Success: no issues found
```

说明：pytest 运行时仍出现 `.pytest_cache` 写入权限警告，属于本地缓存目录权限问题，不影响测试结论。

## 后续建议

1. 增加真实联网 smoke 测试记录，包括 DeepSeek、搜索 Provider 和目标网页抓取成功率。
2. 为 LLM 调用增加更细粒度的 token 预算和按角色并发控制。
3. 将规则 Critic 逐步升级为规则加 LLM 双层质检。
4. 引入 Alembic migration，替代启动时自动 `create_all` 的轻量方案。
