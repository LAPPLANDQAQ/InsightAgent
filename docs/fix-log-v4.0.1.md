# v4.0.1 修复日志

日期：2026-05-13

## 背景

本次修复来自 v4.0.1 本地代码审查补丁，目标是提升 InsightAgent 在本地稳定运行时的可靠性、
安全性和前后端契约健壮性。修复保持运行时只使用 DeepSeek 的约束，不引入新的模型提供方，
不扩展不相关功能。

## 修复范围

### LLM 空内容与失败脱敏

- DeepSeek 返回空内容时不再立即失败，会按当前模型重试。
- 当前模型重试仍为空内容时，会切换到 fallback 模型。
- LLM 失败摘要和诊断预览统一使用脱敏逻辑，避免泄露 key、token、secret、password、Bearer、`sk-*` 和 `tvly-*`。

### 任务执行超时

- 任务执行使用 `TASK_TIMEOUT_SECONDS` 进行整体超时控制，默认 900 秒。
- 超时任务会被标记为 `FAILED`，错误信息写入状态和数据库。
- 超时后并发槽会释放，后续任务可以继续执行。

### 状态阶段文案

- 后端阶段标签统一为英文，移除原先可能出现的中文乱码。
- 覆盖主工作流和可选 RAG 工作流阶段。
- 前端阶段列表同步为英文，避免显示不一致。

### 搜索提供方可靠性

- 搜索服务新增单个提供方超时控制 `SEARCH_PROVIDER_TIMEOUT_SECONDS`，默认 10 秒。
- 单个搜索提供方超时或失败不会阻断其他搜索提供方。
- 搜索失败警告和日志中的异常文本统一脱敏。

### 抓取与解析失败可观测性

- `trafilatura` 解析失败时记录警告，随后继续使用 BeautifulSoup 或正则 fallback。
- 抓取失败返回给上层的错误字段统一脱敏。

### 配置对象安全

- `DEEPSEEK_API_KEY`、`TAVILY_API_KEY`、`MCP_HTTP_AUTH_TOKEN` 在 `model_dump()` 中排除。
- 同一批敏感字段在 `Settings.__repr__()` 中也不再显示。

### API 队列满退避

- 创建任务遇到队列满时，API 返回 HTTP 429。
- 429 响应增加 `Retry-After: 30` header，便于客户端退避重试。

### Streamlit 前端健壮性

- 前端对任务状态轮询中的 429、503、超时和网络抖动进行短暂重试。
- 前端读取后端响应时增加必需字段校验，避免响应结构改动导致隐式崩溃。
- 任务达到最终状态后，报告接口短暂返回 404 时会进行有限重试。

## 新增测试

- DeepSeek 空内容重试、fallback 和失败脱敏测试。
- 任务超时、并发槽释放和失败信息脱敏测试。
- 阶段标签英文和 ASCII 测试。
- 统一脱敏 helper 测试。
- Settings 敏感字段 dump 和 repr 排除测试。
- 搜索提供方超时、全部失败和警告脱敏测试。
- 抓取解析异常日志和抓取错误脱敏测试。
- API 429 `Retry-After` 集成测试。
- Streamlit transient HTTP 判断、响应字段校验和报告重试测试。

## 验证结果

本地验证命令：

```bash
python -B -m pytest -p no:cacheprovider tests -q
python -m ruff check app tests frontend
python -m mypy app --ignore-missing-imports
python -m compileall app
git diff --check
```

验证结论：

- 全量测试通过。
- Ruff 通过。
- Mypy 通过。
- Compileall 通过。
- `git diff --check` 无空白错误。

说明：Windows 环境下 pytest 退出阶段可能出现临时目录清理的 ignored `PermissionError`，
该信息发生在测试完成之后，不代表测试失败。

## 未纳入事项

- 未新增模型提供方。
- 未新增云部署、消息队列、认证或支付能力。
- 未引入真实外部 API 调用测试。
- 未将未跟踪的综合审查草稿自动纳入本次提交。
