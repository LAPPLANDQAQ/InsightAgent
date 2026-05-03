# InsightAgent — Codex 执行规约 v6（审查修复版）

> 本文档是给代码生成器的执行指令，不是给人读的说明。  
> 每条规则都必须严格遵守。冲突时，本文档优先级最高。  
> 实现顺序：从 §0 开始，依次执行每个 Commit，不得跳跃。


> v6 修复重点：
> 1. 修复 agents 导入 `app.infra.llm.base` 与架构测试互相冲突的问题。
> 2. 修复 `.env.example` 中 Tavily 占位 API Key 导致默认搜索失败的问题。
> 3. 补齐 `duckduckgo_search` / `PyMySQL` 依赖，避免 Commit 6/12 运行时报错。
> 4. 扩展千问模型守卫：允许 qwen/qwq 前缀的千问系列模型，拒绝 GPT/Claude/DeepSeek/本地模型。
> 5. 修复 Researcher 未使用 `max_rounds`、无全局 try-except、证据重复、`__import__` hack 等问题。
> 6. 修复 Search/Fetch 缓存 Key 与失败缓存策略。
> 7. 修复 TaskService 后台任务、状态查询、用户指定竞品/维度未传入工作流、API 循环导入等问题。
> 8. 补充 E2E 不允许 `pass` 占位的验收约束。

---

## 0. 执行规则（先读完再动手）

### 0.1 必须遵守

```
- Python 3.12，FastAPI + LangGraph + Pydantic v2 + SQLAlchemy 2.x
- 严格分层:api → services → graph → agents → tools → infra
- 单文件 ≤ 300 行,函数 ≤ 50 行
- 所有公共函数有 Google 风格 docstring
- 所有 Agent / Tool 输出经 Pydantic 校验
- 所有外部依赖经 Protocol 抽象
- 每个 Commit 必须含对应测试且本地通过
- 关键步骤打结构化日志
```

### 0.2 禁止行为

```
× agents/ import app.infra.* 的实现类
  - 唯一例外：agents/ 可以导入 app.infra.llm.base 中的 Protocol / ModelRole / LLMOutputError 类型
  - 禁止导入 app.infra.llm.qwen_dashscope_client 或任何 infra 实现
× agents/ import httpx / openai / anthropic / dashscope / duckduckgo_search / tavily
× tools/ 互相 import
  - 唯一例外：tools/ 可以导入 app.tools.dedup 中的纯函数
× tools/ import services/
× infra/ import agents/ 或 graph/
× 业务运行代码出现 OpenAI / Anthropic / DeepSeek / 本地模型 Provider 实现
  - 注意：openai Python SDK 仅允许在 app/infra/llm/qwen_dashscope_client.py 中作为 DashScope OpenAI 兼容传输层使用
× .env.example 中默认模型名为非千问
× 一次提交 30+ 文件的大爆炸 commit
× 提交未运行的代码
× 工具间硬编码模型名(只能用 model_role)
× tests/integration/ 或 tests/e2e/ 出现 pass / TODO 占位
```

### 0.3 千问运行时硬边界

```
运行时 LLMClient 实现仅允许:
  app/infra/llm/qwen_dashscope_client.py

千问模型守卫规则(写入 config.py):
  允许：模型名以 qwen 或 qwq 开头，例如 qwen-max / qwen-plus / qwen-turbo / qwen-flash / qwen-long / qwen3.5-plus / qwen3.5-flash / qwen-max-latest / qwq-plus
  禁止：gpt / claude / deepseek / kimi / glm / yi / moonshot / local / ollama / llama 等非千问运行时模型

业务代码使用 model_role: heavy / light / fallback
真实模型名仅在 .env / config.py 中
```

### 0.4 Commit 顺序(严格按序)

```
Commit 0:  scripts/verify_qwen_api.py(开工验证)
Commit 1:  骨架 + 配置 + 模型守卫
Commit 2:  schemas/
Commit 3:  L0 Protocol 接口
Commit 4:  Fake/Stub 测试基础
Commit 5:  缓存 + 日志
Commit 6:  搜索 + 抓取(含联网验证)
Commit 7:  QwenDashScopeClient
Commit 8:  Tool 层
Commit 9:  Planner + Researcher
Commit 10: Analyst + Writer + Rule-based Critic
Commit 11: LangGraph Workflow
Commit 12: FastAPI + Service + DB
Commit 13: 前端 + E2E + 演示缓存 + 文档
```

每个 Commit 完成后必须运行:

```
pytest tests/architecture/ -v
pytest tests/unit/ -v
ruff check app/ tests/
```

全部通过才能开始下一个 Commit。

---

## 1. 目录结构(完全按此创建)

```
insight-agent/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── container.py
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── qwen_dashscope_client.py
│   │   │   └── fake_client.py
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── tavily.py
│   │   │   ├── duckduckgo.py
│   │   │   └── service.py
│   │   ├── fetch/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── httpx_client.py
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── sqlite_cache.py
│   │   │   └── memory_cache.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── repository.py
│   │   └── logger.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── search_tool.py
│   │   ├── webpage_tool.py
│   │   ├── extraction_tool.py
│   │   ├── source_classifier_tool.py
│   │   ├── sufficiency_tool.py
│   │   └── dedup.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── planner.py
│   │   ├── researcher.py
│   │   ├── analyst.py
│   │   ├── writer.py
│   │   └── critic.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── reducers.py
│   │   └── workflow.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── source.py
│   │   ├── evidence.py
│   │   ├── plan.py
│   │   ├── analysis.py
│   │   ├── critic.py
│   │   ├── report.py
│   │   └── task.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_service.py
│   │   ├── report_service.py
│   │   └── metric_service.py
│   └── api/
│       ├── __init__.py
│       └── tasks.py
├── frontend/
│   └── streamlit_app.py
├── scripts/
│   ├── verify_qwen_api.py
│   ├── preload_demo_cache.py
│   └── smoke_live.py
├── tests/
│   ├── conftest.py
│   ├── architecture/
│   │   ├── test_layer_imports.py
│   │   ├── test_no_direct_external_imports.py
│   │   ├── test_runtime_model_guard.py
│   │   ├── test_file_size_limits.py
│   │   └── test_docstrings.py
│   ├── unit/
│   │   ├── tools/
│   │   ├── agents/
│   │   └── schemas/
│   ├── integration/
│   │   └── test_workflow.py
│   ├── e2e/
│   │   └── test_smoke.py
│   └── fixtures/
│       ├── search_results/
│       ├── pages/
│       └── llm_responses/
├── examples/
│   └── sample_report.md
├── data/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 2. Commit 0:scripts/verify_qwen_api.py

### 2.1 目的

验证千问 API 在当前网络环境下的稳定性,在开始正式开发前确认基础设施可用。

### 2.2 实现要求

```
文件:scripts/verify_qwen_api.py
依赖:openai SDK(指向千问兼容端点)、httpx
读取环境变量:DASHSCOPE_API_KEY、LLM_BASE_URL

执行 5 种测试,每种重复 3 次,记录成功率与平均延迟:

测试 1:基础文本生成
  prompt: "请用一句话介绍 Python"
  model: qwen-turbo
  期望:稳定返回非空字符串

测试 2:response_format=json_object
  prompt: '请输出一个 JSON,包含 name 和 age 字段。直接输出 JSON。'
  model: qwen-turbo
  response_format: {"type": "json_object"}
  期望:返回合法 JSON

测试 3:强约束 prompt + ```json``` 提取
  prompt: '请输出 JSON: {"name": "...", "age": ...}。包裹在 ```json``` 代码块中。'
  model: qwen-turbo
  期望:提取代码块后解析成功

测试 4:长 prompt 接近 max_tokens
  prompt: 重复 "你好" 1500 次后追加 "请总结上述文本"
  model: qwen-turbo, max_tokens=500
  期望:不超时,返回有意义内容

测试 5:高频连续调用
  连续 10 次 prompt: "1+1="
  model: qwen-turbo
  期望:无限流错误

输出格式:
  打印每个测试的成功率、平均延迟、错误样例
  最后输出建议:
    - 测试 2 成功率 >= 90%: 默认使用 response_format
    - 否则: 默认使用强约束 prompt 模式
```

### 2.3 验收

人工运行此脚本,记录输出。结果不影响 Commit 1 启动,但需要把测试 2 的成功率记入开发笔记,影响 Commit 7 的实现策略。

---

## 3. Commit 1:骨架 + 配置 + 模型守卫

### 3.1 pyproject.toml

```toml
[project]
name = "insight-agent"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.4.0",
  "langgraph>=0.2.0",
  "langchain-core>=0.3.0",
  "sqlalchemy>=2.0.0",
  "alembic>=1.13.0",
  "httpx>=0.27.0",
  "trafilatura>=1.12.0",
  "beautifulsoup4>=4.12.0",
  "python-dotenv>=1.0.0",
  "tenacity>=8.5.0",
  "openai>=1.40.0",
  "duckduckgo_search>=6.2.0",
  "pymysql>=1.1.0",
  "streamlit>=1.37.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pytest-asyncio>=0.23.0",
  "ruff>=0.6.0",
  "mypy>=1.11.0",
  "types-beautifulsoup4",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
warn_unused_ignores = true
warn_redundant_casts = true
warn_return_any = true
# MVP 阶段不要开启 strict=true；当前代码使用 dict 型 LangGraph State，strict 会产生大量噪声。
# V1 稳定后再逐步开启 disallow_untyped_defs / strict_optional 等规则。
strict = false
```

### 3.2 .env.example

```bash
# Runtime
APP_ENV=dev
LOG_LEVEL=INFO

# LLM Provider
# 业务运行时只允许千问；GPT/Claude/DeepSeek 只能用于开发辅助，不能写入运行时配置。
LLM_PROVIDER=qwen_dashscope
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=your_dashscope_key_here
LLM_HEAVY_MODEL=qwen-max
LLM_LIGHT_MODEL=qwen-turbo
LLM_FALLBACK_MODEL=qwen-plus
ENFORCE_QWEN_ONLY=true

# Search
# Tavily API Key 留空时自动跳过 Tavily，只使用 DuckDuckGo。
SEARCH_PROVIDERS=tavily,duckduckgo
TAVILY_API_KEY=

# Cache / DB
CACHE_BACKEND=sqlite
DB_URL=sqlite:///./data/insight.db
MYSQL_URL=

# Concurrency
MAX_CONCURRENT_SEARCH=5
MAX_CONCURRENT_FETCH=8
MAX_CONCURRENT_LLM_HEAVY=2
MAX_CONCURRENT_LLM_LIGHT=5

# Workflow
MAX_ITERATIONS=3
MAX_SEARCH_ROUNDS_PER_COMPETITOR=3
SUFFICIENCY_THRESHOLD=0.6
ENABLE_LLM_CRITIC=false

# Cost guard
MAX_HEAVY_CALLS_PER_TASK=8
MAX_HEAVY_TOKENS_PER_TASK=35000
MAX_LIGHT_TOKENS_PER_TASK=100000
```

### 3.3 app/config.py

```python
"""
Module: app.config
Layer: 配置层
Purpose: 加载环境变量,校验运行时模型守卫
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(ValueError):
    """配置非法时抛出。"""


# 显式列出常用千问模型，同时允许 qwen/qwq 前缀以兼容 qwen3.x / latest 等新模型名。
QWEN_MODEL_WHITELIST = frozenset({
    "qwen-max", "qwen-plus", "qwen-turbo", "qwen-long", "qwen-flash",
    "qwen-max-latest", "qwen-plus-latest", "qwen-turbo-latest", "qwen-long-latest",
    "qwen3-max", "qwen3.5-plus", "qwen3.5-flash", "qwq-plus",
})
FORBIDDEN_MODEL_KEYWORDS = (
    "gpt", "claude", "deepseek", "kimi", "moonshot", "glm", "yi", "llama",
    "ollama", "local", "mistral", "gemini",
)


def is_qwen_model_name(name: str) -> bool:
    """判断模型名是否属于千问运行时允许范围。

    Args:
        name: 模型名。

    Returns:
        True 表示允许作为业务运行时模型。
    """
    normalized = name.strip().lower()
    if not normalized:
        return False
    if any(k in normalized for k in FORBIDDEN_MODEL_KEYWORDS):
        return False
    return normalized in QWEN_MODEL_WHITELIST or normalized.startswith(("qwen", "qwq"))


class Settings(BaseSettings):
    """全局配置。启动时自动校验。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "prod", "test"] = "dev"
    log_level: str = "INFO"

    llm_provider: Literal["qwen_dashscope"] = "qwen_dashscope"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_api_key: str = ""
    llm_heavy_model: str = "qwen-max"
    llm_light_model: str = "qwen-turbo"
    llm_fallback_model: str = "qwen-plus"
    enforce_qwen_only: bool = True

    search_providers: str = "tavily,duckduckgo"
    tavily_api_key: str = ""

    cache_backend: Literal["sqlite", "memory"] = "sqlite"
    db_url: str = "sqlite:///./data/insight.db"
    mysql_url: str = ""

    max_concurrent_search: int = Field(default=5, ge=1, le=20)
    max_concurrent_fetch: int = Field(default=8, ge=1, le=30)
    max_concurrent_llm_heavy: int = Field(default=2, ge=1, le=5)
    max_concurrent_llm_light: int = Field(default=5, ge=1, le=20)

    max_iterations: int = Field(default=3, ge=1, le=5)
    max_search_rounds_per_competitor: int = Field(default=3, ge=1, le=6)
    sufficiency_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    enable_llm_critic: bool = False

    max_heavy_calls_per_task: int = Field(default=8, ge=1, le=20)
    max_heavy_tokens_per_task: int = Field(default=35000, ge=1000)
    max_light_tokens_per_task: int = Field(default=100000, ge=1000)

    @model_validator(mode="after")
    def validate_runtime_models(self) -> "Settings":
        """校验业务运行时只使用千问模型。"""
        if self.llm_provider != "qwen_dashscope":
            raise ConfigError("LLM_PROVIDER must be qwen_dashscope in runtime")
        if not self.enforce_qwen_only:
            return self
        for field_name in ("llm_heavy_model", "llm_light_model", "llm_fallback_model"):
            model_name = getattr(self, field_name)
            if not is_qwen_model_name(model_name):
                raise ConfigError(
                    f"{field_name}={model_name!r} is not allowed. "
                    "Runtime models must be Qwen/QwQ only."
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局配置单例。"""
    return Settings()
```

### 3.4 tests/architecture/test_runtime_model_guard.py

```python
"""验证运行时模型守卫。"""

import pytest
from app.config import Settings, is_qwen_model_name, QWEN_MODEL_WHITELIST


@pytest.fixture
def base_env(monkeypatch):
    """设置最小可启动环境。"""
    monkeypatch.setenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "fake_key")
    monkeypatch.setenv("LLM_PROVIDER", "qwen_dashscope")
    monkeypatch.setenv("ENFORCE_QWEN_ONLY", "true")


def test_settings_reject_gpt(base_env, monkeypatch):
    """业务运行时拒绝 GPT 模型名。"""
    monkeypatch.setenv("LLM_HEAVY_MODEL", "gpt-5.5")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "qwen-turbo")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    with pytest.raises(Exception, match="Qwen"):
        Settings()


def test_settings_reject_claude(base_env, monkeypatch):
    """业务运行时拒绝 Claude 模型名。"""
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen-max")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "claude-3-haiku")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    with pytest.raises(Exception, match="Qwen"):
        Settings()


def test_settings_reject_deepseek(base_env, monkeypatch):
    """业务运行时拒绝 DeepSeek 模型名。"""
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen-max")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    with pytest.raises(Exception, match="Qwen"):
        Settings()


def test_settings_accept_qwen(base_env, monkeypatch):
    """业务运行时接受千问模型名。"""
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen-max")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "qwen-turbo")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    s = Settings()
    assert s.llm_heavy_model == "qwen-max"


def test_settings_accept_new_qwen_prefix(base_env, monkeypatch):
    """允许 qwen/qwq 前缀的新千问模型名。"""
    monkeypatch.setenv("LLM_HEAVY_MODEL", "qwen3.5-plus")
    monkeypatch.setenv("LLM_LIGHT_MODEL", "qwen3.5-flash")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwq-plus")
    s = Settings()
    assert s.llm_light_model == "qwen3.5-flash"


def test_whitelist_completeness():
    """白名单必须包含主流千问模型。"""
    assert "qwen-max" in QWEN_MODEL_WHITELIST
    assert "qwen-turbo" in QWEN_MODEL_WHITELIST
    assert "qwen-plus" in QWEN_MODEL_WHITELIST
    assert is_qwen_model_name("qwen-max-latest")
```

### 3.5 tests/architecture/test_no_direct_external_imports.py

```python
"""验证运行时代码不直接 import 禁用的第三方 SDK。"""

import ast
from pathlib import Path

FORBIDDEN_BASE = {"anthropic", "deepseek"}
FORBIDDEN_IN_AGENTS = {
    "httpx", "openai", "anthropic", "dashscope",
    "duckduckgo_search", "tavily",
}
RUNTIME_DIRS = ["agents", "graph", "services", "api"]
APP_ROOT = Path("app")
LLM_PROTOCOL_IMPORT = "app.infra.llm.base"


def _iter_imports(py_file: Path):
    """遍历 Python 文件中的 import。"""
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_runtime_not_import_forbidden_sdk():
    """运行时上层代码不得导入 Anthropic/DeepSeek SDK。"""
    for dir_name in RUNTIME_DIRS:
        for py in (APP_ROOT / dir_name).rglob("*.py"):
            for name in _iter_imports(py):
                base = name.split(".")[0].lower()
                assert base not in FORBIDDEN_BASE, f"{py} imports forbidden SDK: {name}"


def test_openai_sdk_only_used_by_qwen_client():
    """openai SDK 只能在千问兼容客户端中作为传输层使用。"""
    allowed = APP_ROOT / "infra" / "llm" / "qwen_dashscope_client.py"
    for py in APP_ROOT.rglob("*.py"):
        for name in _iter_imports(py):
            if name.split(".")[0].lower() == "openai":
                assert py == allowed, f"openai SDK only allowed in {allowed}, found in {py}"


def test_agents_not_import_external_libs():
    """Agent 不得直接导入外部 SDK。"""
    for py in (APP_ROOT / "agents").rglob("*.py"):
        for name in _iter_imports(py):
            base = name.split(".")[0].lower()
            assert base not in FORBIDDEN_IN_AGENTS, f"{py} imports forbidden lib: {name}"


def test_agents_not_import_infra_implementations():
    """Agent 只允许导入 LLM Protocol,不得导入 infra 实现。"""
    for py in (APP_ROOT / "agents").rglob("*.py"):
        for name in _iter_imports(py):
            if name == LLM_PROTOCOL_IMPORT:
                continue
            assert not name.startswith("app.infra"), f"{py} imports infra implementation: {name}"


def test_tools_not_import_each_other():
    """工具间禁止互相调用,只允许复用 dedup 纯函数。"""
    tools_dir = APP_ROOT / "tools"
    for py in tools_dir.rglob("*.py"):
        if py.name in {"__init__.py", "dedup.py"}:
            continue
        for name in _iter_imports(py):
            if name.startswith("app.tools.") and name != "app.tools.dedup":
                raise AssertionError(f"{py} imports another tool: {name}")
```

### 3.6 tests/architecture/test_layer_imports.py

```python
"""验证分层依赖方向。"""

import ast
from pathlib import Path

APP_ROOT = Path("app")


def _imports_of(py_file: Path) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


def test_infra_not_import_upper_layers():
    for py in (APP_ROOT / "infra").rglob("*.py"):
        for name in _imports_of(py):
            for forbidden in ("app.agents", "app.graph", "app.services", "app.api"):
                assert not name.startswith(forbidden), (
                    f"{py} imports upper layer: {name}"
                )


def test_tools_not_import_upper_layers():
    for py in (APP_ROOT / "tools").rglob("*.py"):
        for name in _imports_of(py):
            for forbidden in ("app.agents", "app.graph", "app.services", "app.api"):
                assert not name.startswith(forbidden), (
                    f"{py} imports upper layer: {name}"
                )
```

### 3.7 tests/architecture/test_file_size_limits.py

```python
"""验证文件行数限制。"""

from pathlib import Path

MAX_LINES = 300
WHITELIST = {"app/config.py"}  # 配置文件可放宽


def test_file_size():
    for py in Path("app").rglob("*.py"):
        rel = str(py).replace("\\", "/")
        if rel in WHITELIST:
            continue
        lines = len(py.read_text(encoding="utf-8").splitlines())
        assert lines <= MAX_LINES, f"{py} has {lines} lines (max {MAX_LINES})"
```

### 3.8 tests/architecture/test_docstrings.py

```python
"""验证公共函数有 docstring。"""

import ast
from pathlib import Path


def test_public_functions_have_docstrings():
    for py in Path("app").rglob("*.py"):
        if py.name == "__init__.py":
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                assert ast.get_docstring(node), (
                    f"{py}::{node.name} missing docstring"
                )
```

### 3.9 README.md(初稿)

```markdown
# InsightAgent

基于 LangGraph 的多 Agent 竞品分析系统。

## 状态

V0 开发中。

## 快速启动

```bash
cp .env.example .env
# 填入 DASHSCOPE_API_KEY 与 TAVILY_API_KEY
pip install -e ".[dev]"
pytest
```

## 文档

完整规约见 `docs/spec.md`。
```

### 3.10 验收

```
pytest tests/architecture/ -v
ruff check app/ tests/
```

---

## 4. Commit 2:schemas/

### 4.1 app/schemas/source.py

```python
"""信息来源数据契约。"""

from typing import Literal
from pydantic import BaseModel, Field

SourceType = Literal[
    "official", "media", "community", "review", "paper", "unknown",
]


class SourceItem(BaseModel):
    """单个信息来源。"""

    source_id: str
    url: str
    domain: str
    title: str
    source_type: SourceType
    credibility_score: float = Field(ge=0.0, le=1.0)
    classification_method: Literal["rule", "llm", "fallback"]
    published_at: str | None = None
    retrieved_at: str
```

### 4.2 app/schemas/evidence.py

```python
"""证据数据契约。"""

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """完整证据。仅用于 Researcher 抽取与持久化。"""

    evidence_id: str
    task_id: str
    competitor_name: str
    dimension: str
    claim: str = Field(max_length=80)
    value: str
    source_id: str
    source_url: str
    quote: str = Field(max_length=200)
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: str


class EvidenceLite(BaseModel):
    """轻量证据。Analyst 只能接收此类型,不含 quote。"""

    evidence_id: str
    competitor_name: str
    dimension: str
    claim: str
    value: str
    source_url: str
    confidence: float


def to_lite(e: EvidenceItem) -> EvidenceLite:
    """将完整证据转为轻量视图。"""
    return EvidenceLite(
        evidence_id=e.evidence_id,
        competitor_name=e.competitor_name,
        dimension=e.dimension,
        claim=e.claim,
        value=e.value,
        source_url=e.source_url,
        confidence=e.confidence,
    )
```

### 4.3 app/schemas/plan.py

```python
"""调研计划数据契约。"""

from pydantic import BaseModel, Field, model_validator


class ResearchPlan(BaseModel):
    """调研计划。Planner 输出。"""

    market: str
    competitors: list[str] = Field(min_length=2, max_length=6)
    dimensions: list[str] = Field(min_length=3, max_length=8)
    search_queries: dict[str, list[str]]
    required_fields: dict[str, list[str]]
    assumptions: list[str] = []
    constraints: list[str] = []

    @model_validator(mode="after")
    def check_required_fields_match_dimensions(self) -> "ResearchPlan":
        """required_fields 的 key 必须与 dimensions 完全一致。

        Researcher 会按 dimension 取 required_fields[dimension],
        key 缺失会 KeyError 导致整个 Researcher 崩溃。

        Raises:
            ValueError: key 不一致时。
        """
        if set(self.required_fields.keys()) != set(self.dimensions):
            raise ValueError(
                f"required_fields keys must match dimensions exactly. "
                f"dimensions={self.dimensions}, "
                f"required_fields_keys={list(self.required_fields.keys())}"
            )
        return self
```

### 4.4 app/schemas/analysis.py

```python
"""分析结果数据契约。"""

from pydantic import BaseModel, Field


class DimensionAnalysis(BaseModel):
    """单维度分析。"""

    dimension: str
    comparison_summary: str
    key_findings: list[str]
    evidence_refs: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: list[str] = []


class AnalysisResult(BaseModel):
    """完整分析结果。"""

    market_summary: str
    competitor_positioning: dict[str, str]
    dimension_analysis: list[DimensionAnalysis]
    opportunities: list[str] = []
    risks: list[str] = []
    recommendation: str
```

### 4.5 app/schemas/critic.py

```python
"""Critic 问题数据契约。"""

from typing import Literal
from pydantic import BaseModel


class CriticIssue(BaseModel):
    """Critic 发现的问题。"""

    issue_type: Literal[
        "missing_evidence",
        "invalid_evidence_ref",
        "dimension_missing",
        "unsupported_claim",
        "weak_source",
        "format_error",
        "logic_gap",
    ]
    severity: Literal["low", "medium", "high"]
    target_stage: Literal["researcher", "analyst", "writer"]
    message: str
    related_ids: list[str] = []
```

### 4.6 app/schemas/task.py

```python
"""任务相关请求与响应。"""

from typing import Literal
from pydantic import BaseModel, Field

TaskStatus = Literal[
    "PENDING", "RUNNING", "COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED",
]


class CreateTaskRequest(BaseModel):
    """创建任务请求。"""

    query: str = Field(min_length=2)
    competitors: list[str] = []
    dimensions: list[str] = []


class TaskStatusResponse(BaseModel):
    """任务状态响应。"""

    task_id: str
    status: TaskStatus
    current_stage: str | None = None
    progress: float = 0.0
    issues: list[str] = []
```

### 4.7 app/schemas/report.py

```python
"""报告响应。"""

from pydantic import BaseModel
from app.schemas.task import TaskStatus


class ReportResponse(BaseModel):
    """报告响应。"""

    task_id: str
    status: TaskStatus
    report_markdown: str
    quality_metrics: dict[str, float]
```

### 4.8 单元测试 tests/unit/schemas/

```python
# tests/unit/schemas/test_research_plan.py
import pytest
from pydantic import ValidationError
from app.schemas.plan import ResearchPlan


def test_required_fields_match_passes():
    plan = ResearchPlan(
        market="AI 编程助手",
        competitors=["Cursor", "Copilot"],
        dimensions=["定价", "功能", "生态"],
        search_queries={"Cursor": ["Cursor pricing"]},
        required_fields={
            "定价": ["price"],
            "功能": ["features"],
            "生态": ["integrations"],
        },
    )
    assert plan.market == "AI 编程助手"


def test_required_fields_mismatch_fails():
    with pytest.raises(ValidationError, match="must match dimensions"):
        ResearchPlan(
            market="x",
            competitors=["a", "b"],
            dimensions=["A", "B", "C"],
            search_queries={},
            required_fields={"A": ["x"], "B": ["y"]},
        )


def test_competitors_min_length():
    with pytest.raises(ValidationError):
        ResearchPlan(
            market="x",
            competitors=["a"],
            dimensions=["A", "B", "C"],
            search_queries={},
            required_fields={"A": [], "B": [], "C": []},
        )


# tests/unit/schemas/test_evidence.py
from app.schemas.evidence import EvidenceItem, to_lite


def test_to_lite_drops_quote():
    e = EvidenceItem(
        evidence_id="ev_x",
        task_id="t1",
        competitor_name="Cursor",
        dimension="定价",
        claim="个人版 $20/月",
        value="$20",
        source_id="src_1",
        source_url="https://cursor.com/pricing",
        quote="原文片段...",
        confidence=0.9,
        extracted_at="2025-01-01T00:00:00Z",
    )
    lite = to_lite(e)
    assert not hasattr(lite, "quote")
    assert lite.evidence_id == "ev_x"
```

### 4.9 验收

```
pytest tests/architecture/ tests/unit/schemas/ -v
```

---

## 5. Commit 3:L0 Protocol 接口

### 5.1 app/infra/llm/base.py

```python
"""LLM 客户端接口。业务代码只通过此接口调用 LLM。"""

from typing import Protocol, TypeVar, Type, Literal
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

ModelRole = Literal["heavy", "light", "fallback"]


class LLMOutputError(Exception):
    """LLM 输出无法解析为目标 schema 时抛出。"""


class LLMClient(Protocol):
    """统一 LLM 调用接口。"""

    async def invoke(
        self,
        *,
        prompt: str,
        model_role: ModelRole,
        schema: Type[T] | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: float = 30.0,
    ) -> T | str:
        """调用 LLM 并返回结果。

        Args:
            prompt: 输入提示词。
            model_role: 模型角色,由 Provider 映射到具体模型名。
            schema: 传入则强制 JSON 输出并解析。
            max_tokens: 最大输出 token。
            temperature: 采样温度。
            timeout: 超时秒数。

        Returns:
            schema 非空时返回 Pydantic 实例,否则返回字符串。

        Raises:
            LLMOutputError: schema 解析三级降级后仍失败。
        """
        ...
```

### 5.2 app/infra/search/base.py

```python
"""搜索接口。"""

from typing import Protocol
from pydantic import BaseModel


class SearchResult(BaseModel):
    """搜索结果。"""

    title: str
    url: str
    snippet: str
    provider: str


class SearchProvider(Protocol):
    """搜索 Provider。"""

    name: str

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """执行搜索。失败时抛异常,由 SearchService 处理切换。"""
        ...
```

### 5.3 app/infra/fetch/base.py

```python
"""网页抓取接口。"""

from typing import Protocol
from pydantic import BaseModel


class FetchResult(BaseModel):
    """抓取结果。失败时 error 非空。"""

    url: str
    title: str
    text: str
    status_code: int
    error: str | None = None
    fetched_at: str


class FetchClient(Protocol):
    """网页抓取客户端。"""

    async def fetch(self, url: str, timeout: float = 10.0) -> FetchResult:
        """抓取网页正文。失败时不抛异常,通过 error 字段表达。"""
        ...
```

### 5.4 app/infra/cache/base.py

```python
"""缓存接口。"""

from typing import Protocol


class CacheBackend(Protocol):
    """KV 缓存接口。值为 bytes,业务层负责序列化。"""

    async def get(self, key: str) -> bytes | None:
        """获取缓存值,不存在返回 None。"""
        ...

    async def set(self, key: str, value: bytes, ttl: int = 21600) -> None:
        """写入缓存,TTL 默认 6 小时。"""
        ...

    async def delete(self, key: str) -> None:
        """删除缓存。"""
        ...
```

### 5.5 验收

```
pytest tests/architecture/ -v
```

---

## 6. Commit 4:Fake/Stub 测试基础

### 6.1 tests/conftest.py

```python
"""pytest 全局配置。"""

import pytest


@pytest.fixture
def fake_llm():
    from tests.fixtures.fake_llm import FakeLLMClient
    return FakeLLMClient()


@pytest.fixture
def stub_search():
    from tests.fixtures.stub_search import StubSearchProvider
    return StubSearchProvider()


@pytest.fixture
def stub_fetch():
    from tests.fixtures.stub_fetch import StubFetchClient
    return StubFetchClient()
```

### 6.2 tests/fixtures/fake_llm.py

```python
"""Fake LLM 客户端。根据 prompt 关键词返回预设响应。"""

import json
from typing import Type, TypeVar
from pydantic import BaseModel
from app.infra.llm.base import ModelRole, LLMOutputError

T = TypeVar("T", bound=BaseModel)


class FakeLLMClient:
    """测试用 LLM 客户端。

    用法:
        llm = FakeLLMClient()
        llm.set_response(keyword="research_plan", response={"market": "x", ...})
    """

    def __init__(self):
        self.responses: dict[str, dict | str] = {}
        self.calls: list[dict] = []

    def set_response(self, *, keyword: str, response: dict | str) -> None:
        """设置匹配 keyword 的响应。"""
        self.responses[keyword] = response

    async def invoke(
        self,
        *,
        prompt: str,
        model_role: ModelRole,
        schema: Type[T] | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: float = 30.0,
    ) -> T | str:
        """模拟 LLM 调用。"""
        self.calls.append({
            "prompt": prompt[:200],
            "model_role": model_role,
            "schema": schema.__name__ if schema else None,
        })

        for keyword, resp in self.responses.items():
            if keyword in prompt:
                if schema:
                    if isinstance(resp, str):
                        try:
                            return schema(**json.loads(resp))
                        except Exception as exc:
                            raise LLMOutputError(str(exc)) from exc
                    return schema(**resp)
                return resp if isinstance(resp, str) else json.dumps(resp)

        if schema:
            raise LLMOutputError(f"FakeLLM no response for prompt: {prompt[:100]}")
        return ""
```

### 6.3 tests/fixtures/stub_search.py

```python
"""Stub 搜索 Provider。从 fixtures/search_results 读取预设数据。"""

import hashlib
import json
from pathlib import Path
from app.infra.search.base import SearchResult

FIXTURE_DIR = Path(__file__).parent / "search_results"


class StubSearchProvider:
    """测试用搜索 Provider。"""

    name = "stub"

    def __init__(self):
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """从 fixture 文件读取响应。"""
        key = hashlib.md5(query.encode()).hexdigest()
        path = FIXTURE_DIR / f"{key}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [SearchResult(**item) for item in data[:max_results]]
```

### 6.4 tests/fixtures/stub_fetch.py

```python
"""Stub 抓取客户端。"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from app.infra.fetch.base import FetchResult

FIXTURE_DIR = Path(__file__).parent / "pages"


class StubFetchClient:
    """测试用抓取客户端。"""

    def __init__(self):
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    async def fetch(self, url: str, timeout: float = 10.0) -> FetchResult:
        """从 fixture 文件读取页面。"""
        key = hashlib.md5(url.encode()).hexdigest()
        path = FIXTURE_DIR / f"{key}.txt"
        now = datetime.now(timezone.utc).isoformat()
        if not path.exists():
            return FetchResult(
                url=url, title="", text="", status_code=404,
                error="not in fixtures", fetched_at=now,
            )
        text = path.read_text(encoding="utf-8")
        return FetchResult(
            url=url,
            title=text.split("\n")[0][:100] if text else "",
            text=text,
            status_code=200,
            error=None,
            fetched_at=now,
        )
```

### 6.5 验收

```
pytest tests/ -v
```

---

## 7. Commit 5:缓存 + 日志

### 7.1 app/infra/logger.py

```python
"""结构化日志配置。"""

import logging
import sys


def setup_logger(level: str = "INFO") -> None:
    """初始化全局 logger。

    Args:
        level: 日志级别。
    """
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    """获取 logger。"""
    return logging.getLogger(name)
```

### 7.2 app/infra/cache/memory_cache.py

```python
"""内存缓存。"""

import time


class MemoryCache:
    """简单的内存 KV 缓存。"""

    def __init__(self):
        self._store: dict[str, tuple[bytes, float]] = {}

    async def get(self, key: str) -> bytes | None:
        """获取缓存值。"""
        item = self._store.get(key)
        if item is None:
            return None
        value, expire_at = item
        if time.time() > expire_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: bytes, ttl: int = 21600) -> None:
        """写入缓存。"""
        self._store[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        """删除缓存。"""
        self._store.pop(key, None)
```

### 7.3 app/infra/cache/sqlite_cache.py

```python
"""SQLite 持久化缓存。"""

import sqlite3
import time
from pathlib import Path


class SQLiteCache:
    """基于 SQLite 的 KV 缓存。"""

    def __init__(self, db_path: str = "./data/cache.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_table()

    def _init_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    expire_at REAL NOT NULL
                )
            """)

    async def get(self, key: str) -> bytes | None:
        """获取缓存值。"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value, expire_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            value, expire_at = row
            if time.time() > expire_at:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
            return value

    async def set(self, key: str, value: bytes, ttl: int = 21600) -> None:
        """写入缓存。"""
        expire_at = time.time() + ttl
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, expire_at) VALUES (?, ?, ?)",
                (key, value, expire_at),
            )

    async def delete(self, key: str) -> None:
        """删除缓存。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
```

### 7.4 单元测试

```python
# tests/unit/infra/test_cache.py
import pytest
from app.infra.cache.memory_cache import MemoryCache
from app.infra.cache.sqlite_cache import SQLiteCache


@pytest.fixture(params=["memory", "sqlite"])
def cache(request, tmp_path):
    if request.param == "memory":
        return MemoryCache()
    return SQLiteCache(db_path=str(tmp_path / "cache.db"))


@pytest.mark.asyncio
async def test_set_get(cache):
    await cache.set("k", b"v")
    assert await cache.get("k") == b"v"


@pytest.mark.asyncio
async def test_get_missing(cache):
    assert await cache.get("nope") is None


@pytest.mark.asyncio
async def test_delete(cache):
    await cache.set("k", b"v")
    await cache.delete("k")
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_ttl_expire(cache):
    import asyncio
    await cache.set("k", b"v", ttl=1)
    await asyncio.sleep(1.1)
    assert await cache.get("k") is None
```

---

## 8. Commit 6:搜索 + 抓取

### 8.1 app/infra/search/tavily.py

```python
"""Tavily 搜索 Provider。"""

import httpx
from app.infra.search.base import SearchProvider, SearchResult


class TavilyProvider:
    """Tavily 搜索实现。"""

    name = "tavily"

    def __init__(self, api_key: str, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """调用 Tavily API。失败时抛异常。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                provider=self.name,
            )
            for item in data.get("results", [])
        ]
```

### 8.2 app/infra/search/duckduckgo.py

```python
"""DuckDuckGo 兜底搜索。"""

from duckduckgo_search import DDGS
from app.infra.search.base import SearchProvider, SearchResult


class DuckDuckGoProvider:
    """DDG 搜索实现。"""

    name = "duckduckgo"

    def __init__(self, region: str = "wt-wt"):
        self.region = region

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """调用 DDG。同步 API,在线程池中执行。"""
        import asyncio

        def _do_search() -> list[dict]:
            with DDGS() as ddgs:
                return list(ddgs.text(query, region=self.region, max_results=max_results))

        results = await asyncio.to_thread(_do_search)
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
                provider=self.name,
            )
            for r in results
        ]
```

### 8.3 app/infra/search/service.py

```python
"""搜索服务。多 Provider 切换 + 缓存 + 限流。"""

import asyncio
import hashlib
import json
import logging
from app.infra.cache.base import CacheBackend
from app.infra.search.base import SearchProvider, SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """统一搜索服务。Tool 层只通过此类访问搜索。"""

    def __init__(
        self,
        providers: list[SearchProvider],
        cache: CacheBackend,
        max_concurrent: int = 5,
    ):
        if not providers:
            raise ValueError("至少需要一个 SearchProvider")
        self.providers = providers
        self.cache = cache
        self._sem = asyncio.Semaphore(max_concurrent)

    async def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        """搜索并缓存结果。

        缓存 Key 必须包含 provider 链和 max_results,否则切换 Provider 或结果数时会误命中。
        """
        provider_chain = ",".join(p.name for p in self.providers)
        raw_key = f"{provider_chain}|{max_results}|{query}"
        cache_key = f"search:{hashlib.md5(raw_key.encode()).hexdigest()}"
        cached = await self.cache.get(cache_key)
        if cached:
            data = json.loads(cached.decode("utf-8"))
            return [SearchResult(**item) for item in data][:max_results]

        async with self._sem:
            for provider in self.providers:
                try:
                    results = await provider.search(query, max_results)
                    if results:
                        payload = json.dumps([r.model_dump() for r in results], ensure_ascii=False)
                        await self.cache.set(cache_key, payload.encode("utf-8"))
                        return results
                except Exception as exc:
                    logger.warning(
                        "search_provider_failed",
                        extra={"provider": provider.name, "query": query, "error": str(exc)},
                    )
        return []
```

### 8.4 app/infra/fetch/httpx_client.py

```python
"""基于 httpx + trafilatura 的抓取客户端。"""

import hashlib
import json
import logging
from datetime import datetime, timezone
import httpx
import trafilatura
from bs4 import BeautifulSoup
from app.infra.cache.base import CacheBackend
from app.infra.fetch.base import FetchResult

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 InsightAgent/0.1"
)
FETCH_SUCCESS_TTL = 21600
FETCH_FAILURE_TTL = 300


class HttpxFetchClient:
    """网页抓取实现。"""

    def __init__(self, cache: CacheBackend, max_text_chars: int = 20000):
        self.cache = cache
        self.max_text_chars = max_text_chars

    async def fetch(self, url: str, timeout: float = 10.0) -> FetchResult:
        """抓取网页正文。

        失败结果只短缓存 5 分钟,避免临时网络错误污染 6 小时缓存。
        """
        cache_key = f"fetch:{hashlib.md5(url.encode()).hexdigest()}"
        cached = await self.cache.get(cache_key)
        if cached:
            return FetchResult(**json.loads(cached.decode("utf-8")))

        now = datetime.now(timezone.utc).isoformat()
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                headers={"User-Agent": UA},
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                status = resp.status_code
                html = resp.text
                if status >= 400:
                    raise httpx.HTTPStatusError(
                        f"HTTP {status}", request=resp.request, response=resp,
                    )

            text = self._extract(html)[: self.max_text_chars]
            title = self._extract_title(html)
            result = FetchResult(
                url=url, title=title, text=text,
                status_code=status, error=None, fetched_at=now,
            )
            ttl = FETCH_SUCCESS_TTL
        except Exception as exc:
            logger.warning("fetch_failed", extra={"url": url, "error": str(exc)})
            result = FetchResult(
                url=url, title="", text="",
                status_code=0, error=str(exc), fetched_at=now,
            )
            ttl = FETCH_FAILURE_TTL

        await self.cache.set(cache_key, result.model_dump_json().encode("utf-8"), ttl=ttl)
        return result

    @staticmethod
    def _extract(html: str) -> str:
        text = trafilatura.extract(html) or ""
        if text.strip():
            return text
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _extract_title(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()[:200]
        return ""
```

### 8.5 联网烟囱测试(开发期手动)

```python
# scripts/smoke_search_fetch.py
"""真实联网验证 Tavily 与 fetch。Commit 6 完成后手动跑一次。"""

import asyncio
import os
from app.infra.cache.memory_cache import MemoryCache
from app.infra.search.service import SearchService
from app.infra.search.tavily import TavilyProvider
from app.infra.search.duckduckgo import DuckDuckGoProvider
from app.infra.fetch.httpx_client import HttpxFetchClient


async def main():
    cache = MemoryCache()
    providers = []
    if os.getenv("TAVILY_API_KEY"):
        providers.append(TavilyProvider(api_key=os.environ["TAVILY_API_KEY"]))
    providers.append(DuckDuckGoProvider())
    service = SearchService(providers, cache)
    fetcher = HttpxFetchClient(cache)

    queries = ["Cursor AI editor pricing", "GitHub Copilot 定价", "Codeium features"]
    for q in queries:
        print(f"\n=== Search: {q} ===")
        results = await service.search(q, max_results=5)
        print(f"got {len(results)} results")
        for r in results[:2]:
            print(f"  - {r.title[:60]} ({r.provider})")

        if results:
            page = await fetcher.fetch(results[0].url)
            print(f"fetched {len(page.text)} chars, error={page.error}")


if __name__ == "__main__":
    asyncio.run(main())
```

运行 `python scripts/smoke_search_fetch.py`,确认至少 5 次搜索不限流。

---

## 9. Commit 7:QwenDashScopeClient

### 9.1 app/infra/llm/qwen_dashscope_client.py

```python
"""千问 DashScope OpenAI 兼容客户端。业务运行时唯一 LLM 实现。"""

import json
import logging
import re
from contextvars import ContextVar
from typing import Type, TypeVar
from openai import AsyncOpenAI
from openai import APIConnectionError, RateLimitError
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type,
)
from app.infra.llm.base import LLMClient, LLMOutputError, ModelRole

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

# 当次任务的 token 用量,由上层在任务边界 reset/读取
_token_ctx: ContextVar[dict | None] = ContextVar("_token_ctx", default=None)


def reset_token_ctx() -> None:
    """重置当前任务的 token 计数。"""
    _token_ctx.set({
        "heavy_input": 0, "heavy_output": 0,
        "light_input": 0, "light_output": 0,
        "heavy_calls": 0, "light_calls": 0,
    })


def get_token_usage() -> dict:
    """读取当前任务的 token 用量。"""
    ctx = _token_ctx.get()
    return dict(ctx) if ctx else {}


class QwenDashScopeClient(LLMClient):
    """千问客户端。

    schema 解析三级降级:
    1. response_format=json_object + 直接解析
    2. 强约束 prompt + ```json``` 代码块提取
    3. 二次修复 prompt(让模型修正上次输出)
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        heavy_model: str,
        light_model: str,
        fallback_model: str,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.models = {
            "heavy": heavy_model,
            "light": light_model,
            "fallback": fallback_model,
        }

    async def invoke(
        self,
        *,
        prompt: str,
        model_role: ModelRole,
        schema: Type[T] | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: float = 30.0,
    ) -> T | str:
        """调用千问。详见 LLMClient 接口。"""
        model_name = self.models[model_role]

        if schema is None:
            text = await self._call_text(
                model_name, prompt, max_tokens, temperature, timeout, model_role,
            )
            return text

        # 三级降级
        try:
            return await self._call_with_json_mode(
                model_name, prompt, schema, max_tokens, temperature, timeout, model_role,
            )
        except (LLMOutputError, ValidationError, json.JSONDecodeError) as exc1:
            logger.info("json_mode_failed_fallback_to_prompt", extra={"err": str(exc1)})

        try:
            return await self._call_with_strict_prompt(
                model_name, prompt, schema, max_tokens, temperature, timeout, model_role,
            )
        except (LLMOutputError, ValidationError, json.JSONDecodeError) as exc2:
            logger.info("strict_prompt_failed_fallback_to_repair", extra={"err": str(exc2)})

        try:
            return await self._call_with_repair(
                model_name, prompt, schema, max_tokens, temperature, timeout, model_role,
            )
        except Exception as exc3:
            raise LLMOutputError(f"three-tier degradation failed: {exc3}") from exc3

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    )
    async def _raw_call(
        self,
        *,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        timeout: float,
        response_format: dict | None = None,
        model_role: ModelRole,
    ) -> tuple[str, int, int]:
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": timeout,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self.client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        self._record(model_role, in_tok, out_tok)
        return text, in_tok, out_tok

    def _record(self, role: ModelRole, in_tok: int, out_tok: int) -> None:
        ctx = _token_ctx.get()
        if ctx is None:
            return
        bucket = "heavy" if role == "heavy" else "light"
        ctx[f"{bucket}_input"] += in_tok
        ctx[f"{bucket}_output"] += out_tok
        ctx[f"{bucket}_calls"] += 1

    async def _call_text(
        self, model, prompt, max_tokens, temperature, timeout, role,
    ) -> str:
        text, _, _ = await self._raw_call(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            model_role=role,
        )
        return text

    async def _call_with_json_mode(
        self, model, prompt, schema, max_tokens, temperature, timeout, role,
    ):
        text, _, _ = await self._raw_call(
            model=model,
            messages=[
                {"role": "system", "content": "你是输出严格 JSON 的助手。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            response_format={"type": "json_object"},
            model_role=role,
        )
        return schema.model_validate_json(text)

    async def _call_with_strict_prompt(
        self, model, prompt, schema, max_tokens, temperature, timeout, role,
    ):
        schema_desc = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        wrapped = (
            f"{prompt}\n\n"
            f"必须严格按以下 JSON Schema 输出,且只输出 JSON,放在 ```json``` 代码块中:\n"
            f"{schema_desc}"
        )
        text, _, _ = await self._raw_call(
            model=model,
            messages=[{"role": "user", "content": wrapped}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            model_role=role,
        )
        json_str = self._extract_json_block(text)
        return schema.model_validate_json(json_str)

    async def _call_with_repair(
        self, model, prompt, schema, max_tokens, temperature, timeout, role,
    ):
        # 先调一次拿到原始响应,再让模型修复
        raw, _, _ = await self._raw_call(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            model_role=role,
        )
        schema_desc = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        repair_prompt = (
            f"以下文本应该是符合 Schema 的 JSON,但可能有格式错误。"
            f"请输出修正后的合法 JSON,放在 ```json``` 代码块中。\n\n"
            f"原始文本:\n{raw}\n\nSchema:\n{schema_desc}"
        )
        text, _, _ = await self._raw_call(
            model=model,
            messages=[{"role": "user", "content": repair_prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
            timeout=timeout,
            model_role=role,
        )
        json_str = self._extract_json_block(text)
        return schema.model_validate_json(json_str)

    @staticmethod
    def _extract_json_block(text: str) -> str:
        m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        # 退化:寻找第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end + 1]
        raise LLMOutputError("no JSON block found in response")
```

### 9.2 验收

```python
# tests/unit/infra/test_qwen_client.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.infra.llm.qwen_dashscope_client import (
    QwenDashScopeClient, reset_token_ctx, get_token_usage,
)
from pydantic import BaseModel


class FakeResp(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_text_call(monkeypatch):
    client = QwenDashScopeClient(
        api_key="x", base_url="http://x",
        heavy_model="qwen-max", light_model="qwen-turbo", fallback_model="qwen-plus",
    )
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="hi"))]
    mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
    client.client.chat.completions.create = AsyncMock(return_value=mock_resp)

    reset_token_ctx()
    text = await client.invoke(prompt="x", model_role="light")
    assert text == "hi"
    usage = get_token_usage()
    assert usage["light_calls"] == 1
    assert usage["light_input"] == 10
```

---

## 10. Commit 8:Tool 层

### 10.1 app/tools/dedup.py

```python
"""URL 去重工具(纯函数,可被其他 tool 引用)。"""

from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

UTM_PREFIXES = ("utm_", "fbclid", "gclid", "ref")


def normalize_url(url: str) -> str:
    """规范化 URL:小写域名、去 UTM、去末尾斜杠、统一协议。"""
    p = urlparse(url.strip())
    scheme = p.scheme.lower() or "https"
    netloc = p.netloc.lower()
    path = p.path.rstrip("/") or "/"
    query = urlencode([
        (k, v) for k, v in parse_qsl(p.query)
        if not any(k.startswith(prefix) for prefix in UTM_PREFIXES)
    ])
    return urlunparse((scheme, netloc, path, "", query, ""))


def dedup_results(results: list) -> list:
    """对包含 url 字段的对象列表去重,保留首次出现。"""
    seen: set[str] = set()
    out = []
    for r in results:
        url = r.url if hasattr(r, "url") else r["url"]
        key = normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
```

### 10.2 app/tools/search_tool.py

```python
"""搜索工具。封装 SearchService。"""

from app.infra.search.base import SearchResult
from app.infra.search.service import SearchService


class SearchTool:
    """搜索工具。Agent 通过此类调搜索。"""

    def __init__(self, search_service: SearchService):
        self.search_service = search_service

    async def run(self, query: str, max_results: int = 8) -> list[SearchResult]:
        """执行搜索。

        Args:
            query: 搜索词。
            max_results: 结果数上限。

        Returns:
            搜索结果列表(可能为空)。
        """
        return await self.search_service.search(query, max_results)
```

### 10.3 app/tools/webpage_tool.py

```python
"""网页抓取与摘要工具。"""

import hashlib
import logging
from app.infra.cache.base import CacheBackend
from app.infra.fetch.base import FetchClient, FetchResult
from app.infra.llm.base import LLMClient

logger = logging.getLogger(__name__)
SUMMARY_THRESHOLD = 4000
SUMMARY_TARGET = 1500


class WebpageTool:
    """网页抓取工具。长文自动用 light 模型摘要。"""

    def __init__(
        self,
        fetch_client: FetchClient,
        llm: LLMClient,
        cache: CacheBackend,
    ):
        self.fetch_client = fetch_client
        self.llm = llm
        self.cache = cache

    async def run(self, url: str) -> FetchResult:
        """抓取并必要时摘要。

        Args:
            url: 目标 URL。

        Returns:
            抓取结果。text 字段长度不超过 SUMMARY_THRESHOLD。
        """
        result = await self.fetch_client.fetch(url)
        if result.error or not result.text:
            return result
        if len(result.text) <= SUMMARY_THRESHOLD:
            return result

        cache_key = f"summary:{hashlib.md5(url.encode()).hexdigest()}:light"
        cached = await self.cache.get(cache_key)
        if cached:
            result.text = cached.decode("utf-8")
            return result

        prompt = (
            f"请将以下网页正文压缩到 {SUMMARY_TARGET} 字以内,"
            f"保留关键事实(产品名、定价、功能、用户评价等),不要发挥。\n\n"
            f"{result.text[:8000]}"
        )
        try:
            summary = await self.llm.invoke(
                prompt=prompt,
                model_role="light",
                max_tokens=1200,
                temperature=0.0,
            )
        except Exception as exc:
            logger.warning("summary_failed", extra={"url": url, "error": str(exc)})
            result.text = result.text[:SUMMARY_THRESHOLD]
            return result

        text = summary if isinstance(summary, str) else str(summary)
        await self.cache.set(cache_key, text.encode("utf-8"))
        result.text = text
        return result
```

### 10.4 app/tools/source_classifier_tool.py

```python
"""来源分类工具。规则优先,LLM 兜底。"""

from urllib.parse import urlparse
from app.infra.llm.base import LLMClient
from app.schemas.source import SourceType

# 域名白名单:domain -> (source_type, credibility_score)
DOMAIN_WHITELIST: dict[str, tuple[SourceType, float]] = {
    "github.com": ("community", 0.7),
    "stackoverflow.com": ("community", 0.7),
    "zhihu.com": ("community", 0.6),
    "juejin.cn": ("community", 0.6),
    "v2ex.com": ("community", 0.5),
    "reddit.com": ("community", 0.6),
    "36kr.com": ("media", 0.8),
    "techcrunch.com": ("media", 0.85),
    "infoq.cn": ("media", 0.8),
    "jiqizhixin.com": ("media", 0.8),
    "producthunt.com": ("review", 0.6),
    "g2.com": ("review", 0.7),
    "capterra.com": ("review", 0.7),
    "arxiv.org": ("paper", 0.9),
}

OFFICIAL_TLDS = (".com", ".io", ".ai", ".cn", ".dev")


class SourceClassifierTool:
    """来源分类。"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(
        self, url: str, title: str = "",
    ) -> tuple[SourceType, float, str]:
        """分类来源。

        Args:
            url: 来源 URL。
            title: 网页标题(辅助 LLM 判断)。

        Returns:
            (source_type, credibility_score, classification_method)
            method ∈ {"rule", "llm", "fallback"}
        """
        domain = self._extract_domain(url)

        # 规则匹配
        if domain in DOMAIN_WHITELIST:
            stype, score = DOMAIN_WHITELIST[domain]
            return stype, score, "rule"

        # 简单启发:疑似官网
        if self._looks_like_official(domain, title):
            return "official", 0.9, "rule"

        # LLM 兜底
        try:
            prompt = (
                f"判断以下 URL 的来源类型,只输出一个单词:"
                f"official / media / community / review / paper / unknown。\n"
                f"URL: {url}\nTitle: {title}"
            )
            text = await self.llm.invoke(
                prompt=prompt, model_role="light",
                max_tokens=20, temperature=0.0,
            )
            label = (text if isinstance(text, str) else "").strip().lower()
            if label in {"official", "media", "community", "review", "paper"}:
                score = {
                    "official": 0.85, "media": 0.7,
                    "community": 0.5, "review": 0.5, "paper": 0.85,
                }[label]
                return label, score, "llm"  # type: ignore
        except Exception:
            pass

        return "unknown", 0.3, "fallback"

    @staticmethod
    def _extract_domain(url: str) -> str:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc

    @staticmethod
    def _looks_like_official(domain: str, title: str) -> bool:
        if not domain:
            return False
        # 域名根 == 标题前缀(简单启发)
        root = domain.split(".")[0]
        return len(root) >= 3 and root.lower() in title.lower()
```

### 10.5 app/tools/extraction_tool.py

```python
"""结构化证据抽取工具。"""

import hashlib
import logging
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.infra.llm.base import LLMClient, LLMOutputError
from app.schemas.evidence import EvidenceItem
from app.schemas.source import SourceItem

logger = logging.getLogger(__name__)
MAX_INPUT_CHARS = 2000


class ExtractedField(BaseModel):
    """LLM 抽取出的单个字段。"""

    field: str
    value: str
    quote: str = Field(max_length=200)


class ExtractionResult(BaseModel):
    """LLM 抽取结果。"""

    items: list[ExtractedField] = []


class ExtractionTool:
    """从文本抽取 EvidenceItem。"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(
        self,
        *,
        text: str,
        fields: list[str],
        competitor_name: str,
        dimension: str,
        source: SourceItem,
        task_id: str,
    ) -> list[EvidenceItem]:
        """抽取证据。

        Args:
            text: 待抽取文本(≤ 2000 字)。
            fields: 待抽取字段。
            competitor_name: 竞品名。
            dimension: 维度名。
            source: 来源。
            task_id: 任务 ID。

        Returns:
            EvidenceItem 列表。失败返回空列表。

        Raises:
            ValueError: text 超长或 fields 为空。
        """
        if len(text) > MAX_INPUT_CHARS:
            raise ValueError(f"text length {len(text)} > {MAX_INPUT_CHARS}")
        if not fields:
            raise ValueError("fields must not be empty")

        prompt = self._build_prompt(text, fields, competitor_name, dimension)
        try:
            result = await self.llm.invoke(
                prompt=prompt,
                model_role="light",
                schema=ExtractionResult,
                max_tokens=800,
                temperature=0.0,
            )
            assert isinstance(result, ExtractionResult)
            return self._build_evidences(
                result.items, competitor_name, dimension, source, task_id,
            )
        except (LLMOutputError, ValueError, AssertionError) as exc:
            logger.warning("extract_failed", extra={"error": str(exc), "url": source.url})
            return []

    @staticmethod
    def _build_prompt(text: str, fields: list[str], competitor: str, dimension: str) -> str:
        fields_str = ", ".join(fields)
        return (
            f"从以下关于「{competitor}」的「{dimension}」相关文本中,"
            f"抽取以下字段: {fields_str}。\n"
            f"输出对象格式: {{\"items\": [{{\"field\": \"...\", \"value\": \"...\", \"quote\": \"...\"}}]}}。\n"
            f"quote 必须是原文片段且不超过 200 字。找不到的字段不要输出。不要编造。\n\n"
            f"文本:\n{text}"
        )

    @staticmethod
    def _build_evidences(
        items: list[ExtractedField], competitor: str, dimension: str,
        source: SourceItem, task_id: str,
    ) -> list[EvidenceItem]:
        out: list[EvidenceItem] = []
        now = datetime.now(timezone.utc).isoformat()
        seen: set[str] = set()
        for item in items:
            field = item.field.strip()
            value = item.value.strip()
            quote = item.quote.strip()[:200]
            if not field or not value or not quote:
                continue
            claim = f"{field}: {value}"[:80]
            raw_id = f"{task_id}|{competitor}|{dimension}|{source.url}|{claim}"
            ev_id = "ev_" + hashlib.sha1(raw_id.encode()).hexdigest()[:16]
            if ev_id in seen:
                continue
            seen.add(ev_id)
            out.append(EvidenceItem(
                evidence_id=ev_id,
                task_id=task_id,
                competitor_name=competitor,
                dimension=dimension,
                claim=claim,
                value=value,
                source_id=source.source_id,
                source_url=source.url,
                quote=quote,
                confidence=min(0.95, source.credibility_score + 0.1),
                extracted_at=now,
            ))
        return out
```

### 10.6 app/tools/sufficiency_tool.py

```python
"""信息充分度评分工具。纯函数。"""

from datetime import datetime, timezone
from app.schemas.evidence import EvidenceItem
from app.schemas.source import SourceItem


class SufficiencyTool:
    """充分度评分。"""

    def run(
        self,
        *,
        evidences: list[EvidenceItem],
        sources: list[SourceItem],
        dimension: str,
        required_fields: list[str],
    ) -> float:
        """计算指定维度的充分度评分。

        公式:0.4 * 字段完整度 + 0.3 * 来源质量 + 0.2 * 来源数量 + 0.1 * 时效性

        Args:
            evidences: 当前竞品的全部证据。
            sources: 当前竞品的全部来源。
            dimension: 目标维度。
            required_fields: 该维度的必备字段。

        Returns:
            0.0 - 1.0 的评分。
        """
        dim_evs = [e for e in evidences if e.dimension == dimension]
        if not dim_evs or not required_fields:
            return 0.0

        # 字段完整度
        covered = set()
        for e in dim_evs:
            for f in required_fields:
                if f.lower() in e.claim.lower() or f.lower() in e.value.lower():
                    covered.add(f)
        field_score = len(covered) / len(required_fields)

        # 来源质量
        dim_sources = [s for s in sources if s.url in {e.source_url for e in dim_evs}]
        if dim_sources:
            quality_score = sum(s.credibility_score for s in dim_sources) / len(dim_sources)
        else:
            quality_score = 0.0

        # 来源数量
        unique_domains = {s.domain for s in dim_sources}
        count_score = min(1.0, len(unique_domains) / 2.0)

        # 时效性(简化:无 published_at 视为 0.5)
        recent_score = 0.5

        return round(
            0.4 * field_score + 0.3 * quality_score
            + 0.2 * count_score + 0.1 * recent_score,
            3,
        )
```

### 10.7 验收

```
pytest tests/architecture/ tests/unit/ -v
```

---

## 11. Commit 9:Planner + Researcher

### 11.1 app/agents/base.py

```python
"""Agent 基类。"""

from typing import Any


class AgentBase:
    """所有 Agent 的基类。"""

    name: str = "base"

    async def run(self, state: Any) -> dict:
        """执行 Agent。子类必须实现。

        必须 try-except 全部内部异常,失败时返回 issues 而非抛出。
        """
        raise NotImplementedError
```

### 11.2 app/agents/planner.py

```python
"""调研规划 Agent。"""

import logging
from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient, LLMOutputError
from app.schemas.plan import ResearchPlan

logger = logging.getLogger(__name__)


class Planner(AgentBase):
    """生成 ResearchPlan。"""

    name = "planner"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, state: dict) -> dict:
        """生成调研计划。

        规则:
        1. 用户指定竞品时不替换
        2. 未指定时自动生成 3-5 个
        3. dimensions 控制在 3-6 个
        4. required_fields key 必须与 dimensions 一致(由 Pydantic 校验保证)
        """
        query = state["user_query"]
        requested_competitors = state.get("requested_competitors", [])
        requested_dimensions = state.get("requested_dimensions", [])
        prompt = self._build_prompt(query, requested_competitors, requested_dimensions)

        try:
            plan = await self.llm.invoke(
                prompt=prompt,
                model_role="heavy",
                schema=ResearchPlan,
                max_tokens=1500,
                temperature=0.2,
            )
        except LLMOutputError as exc:
            logger.error("planner_failed", extra={"error": str(exc)})
            return {
                "research_plan": None,
                "issues": [f"Planner 输出无效: {exc}"],
                "task_status": "FAILED",
            }

        return {"research_plan": plan, "current_stage": "planner_done"}

    @staticmethod
    def _build_prompt(query: str, competitors: list[str], dimensions: list[str]) -> str:
        return (
            f"用户希望调研以下赛道:\n{query}\n\n"
            f"用户指定竞品(必须保留,为空则自动选择): {competitors}\n"
            f"用户指定维度(必须保留,为空则自动选择): {dimensions}\n\n"
            f"请生成一个 ResearchPlan,要求:\n"
            f"1. competitors: 2-6 个主流竞品(用户指定的必须保留)\n"
            f"2. dimensions: 3-8 个调研维度,推荐: "
            f"产品定位、核心功能、定价模式、技术与生态、用户反馈、差异化机会\n"
            f"3. required_fields: 每个 dimension 的关键字段列表"
            f"(key 必须与 dimensions 完全一致)\n"
            f"4. search_queries: 每个竞品的初始搜索词\n"
            f"5. 模糊输入必须写入 assumptions"
        )
```

### 11.3 app/agents/researcher.py

```python
"""信息收集 Agent。"""

import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from app.agents.base import AgentBase
from app.schemas.evidence import EvidenceItem
from app.schemas.source import SourceItem
from app.tools.dedup import dedup_results
from app.tools.extraction_tool import ExtractionTool
from app.tools.search_tool import SearchTool
from app.tools.source_classifier_tool import SourceClassifierTool
from app.tools.sufficiency_tool import SufficiencyTool
from app.tools.webpage_tool import WebpageTool

logger = logging.getLogger(__name__)
MAX_FETCH_PER_ROUND = 3
MAX_QUERIES_PER_DIMENSION = 2


class Researcher(AgentBase):
    """搜索 + 抓取 + 抽取。严格不做横向分析。"""

    name = "researcher"

    def __init__(
        self,
        search_tool: SearchTool,
        webpage_tool: WebpageTool,
        extraction_tool: ExtractionTool,
        classifier_tool: SourceClassifierTool,
        sufficiency_tool: SufficiencyTool,
        threshold: float = 0.6,
        max_rounds: int = 3,
    ):
        self.search_tool = search_tool
        self.webpage_tool = webpage_tool
        self.extraction_tool = extraction_tool
        self.classifier_tool = classifier_tool
        self.sufficiency_tool = sufficiency_tool
        self.threshold = threshold
        self.max_rounds = max_rounds

    async def run(self, state: dict) -> dict:
        """执行调研。内部异常全部转为 issues。"""
        try:
            plan = state.get("research_plan")
            if plan is None:
                return {"issues": ["Researcher: research_plan 为空"]}

            existing = {c["name"]: c for c in state.get("competitors", [])}
            updated = []
            for competitor in plan.competitors:
                data = existing.get(competitor) or self._init_competitor(competitor)
                for dimension in plan.dimensions:
                    if data["sufficiency"].get(dimension, 0.0) >= self.threshold:
                        continue
                    await self._research_dimension(data, plan, competitor, dimension, state["task_id"])
                updated.append(data)

            return {"competitors": updated, "current_stage": "researcher_done"}
        except Exception as exc:
            logger.exception("researcher_failed")
            return {"issues": [f"Researcher 失败: {exc}"], "current_stage": "researcher_failed"}

    @staticmethod
    def _init_competitor(name: str) -> dict:
        """初始化竞品数据。"""
        return {
            "name": name,
            "sources": [],
            "evidences": [],
            "sufficiency": {},
            "search_count": 0,
            "fetch_count": 0,
            "failed_urls": [],
        }

    async def _research_dimension(self, data, plan, competitor, dimension, task_id) -> None:
        """对单个竞品的单个维度进行多轮搜索抽取。"""
        for round_idx in range(self.max_rounds):
            if data["sufficiency"].get(dimension, 0.0) >= self.threshold:
                break
            queries = self._build_queries(plan, competitor, dimension, round_idx)
            for q in queries[:MAX_QUERIES_PER_DIMENSION]:
                await self._run_query(data, plan, competitor, dimension, task_id, q)
                score = self._score_dimension(data, dimension, plan.required_fields[dimension])
                data["sufficiency"][dimension] = score
                if score >= self.threshold:
                    break

    async def _run_query(self, data, plan, competitor, dimension, task_id, query) -> None:
        """执行一个查询并抽取证据。"""
        try:
            results = await self.search_tool.run(query, max_results=8)
        except Exception as exc:
            logger.warning("search_error", extra={"query": query, "error": str(exc)})
            return

        data["search_count"] += 1
        for r in dedup_results(results)[:MAX_FETCH_PER_ROUND]:
            source = await self._build_source(r.url, r.title)
            page = await self.webpage_tool.run(r.url)
            data["fetch_count"] += 1
            if page.error or not page.text:
                if r.url not in data["failed_urls"]:
                    data["failed_urls"].append(r.url)
                continue

            evs = await self.extraction_tool.run(
                text=page.text[:2000],
                fields=plan.required_fields[dimension],
                competitor_name=competitor,
                dimension=dimension,
                source=source,
                task_id=task_id,
            )
            self._merge_source(data, source)
            self._merge_evidences(data, evs)

    async def _build_source(self, url: str, title: str) -> SourceItem:
        """构造 SourceItem。"""
        stype, score, method = await self.classifier_tool.run(url, title)
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        return SourceItem(
            source_id="src_" + hashlib.sha1(url.encode()).hexdigest()[:16],
            url=url,
            domain=domain,
            title=title,
            source_type=stype,
            credibility_score=score,
            classification_method=method,  # type: ignore[arg-type]
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _merge_source(data: dict, source: SourceItem) -> None:
        """按 source_id 去重合并来源。"""
        existing_ids = {s["source_id"] for s in data["sources"]}
        if source.source_id not in existing_ids:
            data["sources"].append(source.model_dump())

    @staticmethod
    def _merge_evidences(data: dict, evidences: list[EvidenceItem]) -> None:
        """按 evidence_id 去重合并证据。"""
        existing_ids = {e["evidence_id"] for e in data["evidences"]}
        for e in evidences:
            if e.evidence_id not in existing_ids:
                data["evidences"].append(e.model_dump())
                existing_ids.add(e.evidence_id)

    def _score_dimension(self, data: dict, dimension: str, required_fields: list[str]) -> float:
        """计算维度充分度。"""
        return self.sufficiency_tool.run(
            evidences=[EvidenceItem(**e) for e in data["evidences"]],
            sources=[SourceItem(**s) for s in data["sources"]],
            dimension=dimension,
            required_fields=required_fields,
        )

    @staticmethod
    def _build_queries(plan, competitor: str, dimension: str, round_idx: int) -> list[str]:
        """生成搜索查询。"""
        custom = plan.search_queries.get(competitor, [])
        base = [
            f"{competitor} {dimension}",
            f"{competitor} review {dimension}",
        ]
        if round_idx >= 1:
            base.extend([
                f"{competitor} pricing features docs {dimension}",
                f"{competitor} 用户评价 {dimension}",
            ])
        return custom + base
```

### 11.4 验收

```
pytest tests/unit/agents/test_planner.py tests/unit/agents/test_researcher.py -v
```

---

## 12. Commit 10:Analyst + Writer + Critic

### 12.1 app/agents/analyst.py

```python
"""横向分析 Agent。只接收 EvidenceLite。"""

import logging
from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient, LLMOutputError
from app.schemas.analysis import AnalysisResult
from app.schemas.evidence import EvidenceItem, to_lite

logger = logging.getLogger(__name__)


class Analyst(AgentBase):
    """生成 AnalysisResult。"""

    name = "analyst"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, state: dict) -> dict:
        """执行分析。"""
        plan = state["research_plan"]
        if plan is None:
            return {"issues": ["Analyst: plan 缺失"]}

        # 收集所有 evidences 转 lite
        all_lite = []
        for c in state["competitors"]:
            for e in c["evidences"]:
                all_lite.append(to_lite(EvidenceItem(**e)).model_dump())

        prompt = (
            f"基于以下证据(仅可引用 evidence_id),对竞品做横向分析。\n"
            f"竞品: {plan.competitors}\n"
            f"维度: {plan.dimensions}\n"
            f"证据列表(JSON):\n{all_lite}\n\n"
            f"要求:\n"
            f"1. 每个 dimension_analysis.evidence_refs 至少 1 个 evidence_id\n"
            f"2. 没有证据支撑的结论标注'不足以判断'\n"
            f"3. confidence 由证据数量、来源质量综合给出"
        )

        try:
            result = await self.llm.invoke(
                prompt=prompt, model_role="heavy",
                schema=AnalysisResult, max_tokens=3000, temperature=0.3,
            )
        except LLMOutputError as exc:
            logger.error("analyst_failed", extra={"error": str(exc)})
            return {"issues": [f"Analyst 输出无效: {exc}"]}

        return {"analysis_result": result, "current_stage": "analyst_done"}
```

### 12.2 app/agents/writer.py

```python
"""报告生成 Agent。"""

import logging
from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient

logger = logging.getLogger(__name__)


class Writer(AgentBase):
    """把 AnalysisResult 写成 Markdown。"""

    name = "writer"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, state: dict) -> dict:
        """生成报告。"""
        result = state.get("analysis_result")
        if result is None:
            return {"issues": ["Writer: analysis_result 缺失"]}

        prompt = (
            f"基于以下 AnalysisResult 生成 Markdown 竞品报告。\n"
            f"要求:\n"
            f"1. 章节: 调研概述、竞品概览、分维度对比、竞争格局、选型建议、风险与不确定性、信息来源\n"
            f"2. 引用结论时保留 evidence_id(格式: [ev_xxxx])\n"
            f"3. 不允许新增任何事实\n"
            f"4. 低 confidence 结论必须使用'可能/倾向于/证据有限'等措辞\n\n"
            f"AnalysisResult JSON:\n{result.model_dump_json(indent=2)}"
        )

        try:
            md = await self.llm.invoke(
                prompt=prompt, model_role="heavy",
                max_tokens=3500, temperature=0.4,
            )
        except Exception as exc:
            logger.error("writer_failed", extra={"error": str(exc)})
            return {"issues": [f"Writer 失败: {exc}"]}

        text = md if isinstance(md, str) else str(md)
        return {"draft_report": text, "current_stage": "writer_done"}
```

### 12.3 app/agents/critic.py

```python
"""质量审查 Agent。"""

import logging
import re
from app.agents.base import AgentBase
from app.infra.llm.base import LLMClient
from app.schemas.critic import CriticIssue

logger = logging.getLogger(__name__)


class Critic(AgentBase):
    """Rule-based + 可选 LLM Critic。"""

    name = "critic"

    def __init__(self, llm: LLMClient, enable_llm_critic: bool = False):
        self.llm = llm
        self.enable_llm_critic = enable_llm_critic

    async def run(self, state: dict) -> dict:
        """审查报告。"""
        # iteration 上限熔断
        if state.get("iteration_count", 0) >= state.get("max_iterations", 3):
            return {"last_critic_action": "pass", "issues": [
                "已达最大迭代次数,以下问题仍未完全解决: " + str(state.get("issues", []))
            ]}

        rule_issues = self._check_rules(state)
        if rule_issues:
            action = self._route(rule_issues)
            return {
                "last_critic_action": action,
                "issues": [i.model_dump() for i in rule_issues],
                "iteration_count": state.get("iteration_count", 0) + 1,
            }

        if self.enable_llm_critic:
            llm_issues = await self._check_with_llm(state)
            if llm_issues:
                action = self._route(llm_issues)
                return {
                    "last_critic_action": action,
                    "issues": [i.model_dump() for i in llm_issues],
                    "iteration_count": state.get("iteration_count", 0) + 1,
                }

        return {"last_critic_action": "pass", "issues": []}

    def _check_rules(self, state: dict) -> list[CriticIssue]:
        issues: list[CriticIssue] = []
        analysis = state.get("analysis_result")
        if analysis is None:
            issues.append(CriticIssue(
                issue_type="missing_evidence", severity="high",
                target_stage="analyst", message="analysis_result 为空",
            ))
            return issues

        # 收集所有合法 evidence_id
        valid_ids = set()
        for c in state.get("competitors", []):
            for e in c.get("evidences", []):
                valid_ids.add(e["evidence_id"])

        # 检查每个 dim 的 evidence_refs
        plan = state.get("research_plan")
        covered_dims = {da.dimension for da in analysis.dimension_analysis}
        for da in analysis.dimension_analysis:
            for ref in da.evidence_refs:
                if ref not in valid_ids:
                    issues.append(CriticIssue(
                        issue_type="invalid_evidence_ref", severity="high",
                        target_stage="analyst",
                        message=f"维度 {da.dimension} 引用了不存在的 {ref}",
                        related_ids=[ref],
                    ))

        # 维度覆盖
        if plan:
            missing = set(plan.dimensions) - covered_dims
            for d in missing:
                issues.append(CriticIssue(
                    issue_type="dimension_missing", severity="medium",
                    target_stage="researcher",
                    message=f"维度 {d} 未覆盖",
                ))

        # 报告非空
        report = state.get("draft_report") or ""
        if not report.strip():
            issues.append(CriticIssue(
                issue_type="format_error", severity="high",
                target_stage="writer", message="draft_report 为空",
            ))

        return issues

    @staticmethod
    def _route(issues: list[CriticIssue]) -> str:
        # 优先回退 researcher,其次 analyst,最后 writer
        stages = {i.target_stage for i in issues}
        if "researcher" in stages:
            return "retry_research"
        if "analyst" in stages:
            return "retry_analysis"
        if "writer" in stages:
            return "retry_writing"
        return "pass"

    async def _check_with_llm(self, state: dict) -> list[CriticIssue]:
        # V1 实现,V0 默认关闭
        return []
```

---

## 13. Commit 11:LangGraph Workflow

### 13.1 app/graph/state.py

```python
"""LangGraph 全局状态。"""

from typing import TypedDict, Literal
from app.schemas.plan import ResearchPlan
from app.schemas.analysis import AnalysisResult

TaskStatus = Literal[
    "PENDING", "RUNNING", "COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED",
]


class CompetitorData(TypedDict):
    name: str
    sources: list[dict]
    evidences: list[dict]
    sufficiency: dict[str, float]
    search_count: int
    fetch_count: int
    failed_urls: list[str]


class TokenUsage(TypedDict):
    heavy_input: int
    heavy_output: int
    light_input: int
    light_output: int
    heavy_calls: int
    light_calls: int


class SearchStats(TypedDict):
    total_searches: int
    total_pages_fetched: int
    cache_hits: int
    failed_fetches: int


class ResearchState(TypedDict, total=False):
    task_id: str
    task_status: TaskStatus
    current_stage: str
    user_query: str
    research_plan: ResearchPlan | None
    competitors: list[CompetitorData]
    analysis_result: AnalysisResult | None
    draft_report: str | None
    final_report: str | None
    issues: list
    iteration_count: int
    max_iterations: int
    last_critic_action: str | None
    token_usage: TokenUsage
    search_stats: SearchStats
    quality_metrics: dict[str, float]
    sufficiency_threshold: float
    sufficiency_ok: bool
    requested_competitors: list[str]
    requested_dimensions: list[str]
    elapsed_seconds: float
```

### 13.2 app/graph/reducers.py

```python
"""State 清理与路由函数。"""

DEFAULT_SUFFICIENCY_THRESHOLD = 0.6


def check_sufficiency(state: dict) -> dict:
    """充分度门控。阈值优先从 state 读取,避免写死 0.6。"""
    plan = state.get("research_plan")
    if plan is None:
        return {**state, "sufficiency_ok": False}
    threshold = float(state.get("sufficiency_threshold", DEFAULT_SUFFICIENCY_THRESHOLD))
    ok = True
    for c in state.get("competitors", []):
        for d in plan.dimensions:
            if c["sufficiency"].get(d, 0.0) < threshold:
                ok = False
                break
    return {**state, "sufficiency_ok": ok}


def route_after_sufficiency(state: dict) -> str:
    """充分度路由。"""
    if state.get("iteration_count", 0) >= state.get("max_iterations", 3):
        return "analyst"
    return "analyst" if state.get("sufficiency_ok") else "researcher"


def route_after_critic(state: dict) -> str:
    """Critic 后路由。"""
    if state.get("iteration_count", 0) >= state.get("max_iterations", 3):
        return "finalize"
    action = state.get("last_critic_action")
    return {
        "retry_research": "researcher",
        "retry_analysis": "analyst",
        "retry_writing": "writer",
        "pass": "finalize",
    }.get(action or "pass", "finalize")


def finalize_report(state: dict) -> dict:
    """生成 final_report。"""
    draft = state.get("draft_report") or ""
    issues = state.get("issues") or []
    if not draft.strip():
        draft = "# 竞品分析报告\n\n报告生成失败或证据不足。"
    if state.get("iteration_count", 0) >= state.get("max_iterations", 3) and issues:
        suffix = (
            "\n\n---\n\n## 已知限制\n"
            "已达最大迭代次数,以下问题仍未完全解决:\n"
            + "\n".join(f"- {i if isinstance(i, str) else i.get('message', '')}" for i in issues)
        )
        return {"final_report": draft + suffix, "task_status": "COMPLETED_WITH_WARNINGS"}
    return {"final_report": draft, "task_status": "COMPLETED"}
```

### 13.3 app/graph/workflow.py

```python
"""LangGraph 工作流构建。"""

from langgraph.graph import StateGraph, END
from app.graph.state import ResearchState
from app.graph.reducers import (
    check_sufficiency, route_after_sufficiency,
    route_after_critic, finalize_report,
)


def build_graph(container) -> object:
    """构建并编译 LangGraph。"""
    g = StateGraph(ResearchState)
    g.add_node("planner", container.planner.run)
    g.add_node("researcher", container.researcher.run)
    g.add_node("sufficiency_check", check_sufficiency)
    g.add_node("analyst", container.analyst.run)
    g.add_node("writer", container.writer.run)
    g.add_node("critic", container.critic.run)
    g.add_node("finalize", finalize_report)

    g.set_entry_point("planner")
    g.add_edge("planner", "researcher")
    g.add_edge("researcher", "sufficiency_check")
    g.add_conditional_edges(
        "sufficiency_check",
        route_after_sufficiency,
        {"researcher": "researcher", "analyst": "analyst"},
    )
    g.add_edge("analyst", "writer")
    g.add_edge("writer", "critic")
    g.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "researcher": "researcher",
            "analyst": "analyst",
            "writer": "writer",
            "finalize": "finalize",
        },
    )
    g.add_edge("finalize", END)
    return g.compile()
```

### 13.4 集成测试

```python
# tests/integration/test_workflow.py
"""端到端工作流测试。使用 Fake/Stub。"""

import time
import pytest
from app.graph.workflow import build_graph


@pytest.mark.asyncio
async def test_workflow_one_pass(container_with_stubs):
    """正常一次通过。"""
    graph = build_graph(container_with_stubs)
    started = time.perf_counter()
    final = await graph.ainvoke({
        "task_id": "task_integration_ok",
        "task_status": "RUNNING",
        "user_query": "AI 编程助手赛道",
        "requested_competitors": [],
        "requested_dimensions": [],
        "competitors": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "sufficiency_threshold": 0.6,
        "issues": [],
        "token_usage": {},
    })
    assert time.perf_counter() - started < 5
    assert final["final_report"].strip()
    assert final["task_status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}


@pytest.mark.asyncio
async def test_workflow_retry_once(container_with_retry_stub):
    """Critic 回退一次后通过。"""
    graph = build_graph(container_with_retry_stub)
    final = await graph.ainvoke({
        "task_id": "task_retry_once",
        "task_status": "RUNNING",
        "user_query": "AI 编程助手赛道",
        "requested_competitors": [],
        "requested_dimensions": [],
        "competitors": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "sufficiency_threshold": 0.6,
        "issues": [],
        "token_usage": {},
    })
    assert final["iteration_count"] <= 3
    assert final["final_report"].strip()


@pytest.mark.asyncio
async def test_workflow_max_iterations_break(container_with_bad_critic_stub):
    """达到 max_iterations 后强制 finalize。"""
    graph = build_graph(container_with_bad_critic_stub)
    final = await graph.ainvoke({
        "task_id": "task_break",
        "task_status": "RUNNING",
        "user_query": "AI 编程助手赛道",
        "requested_competitors": [],
        "requested_dimensions": [],
        "competitors": [],
        "iteration_count": 0,
        "max_iterations": 1,
        "sufficiency_threshold": 0.6,
        "issues": [],
        "token_usage": {},
    })
    assert final["task_status"] == "COMPLETED_WITH_WARNINGS"
    assert "已知限制" in final["final_report"]
```


## 14. Commit 12:FastAPI + Service + DB

### 14.1 app/infra/db/models.py

```python
"""SQLAlchemy 模型。"""

from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40))
    current_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(40))
    draft_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceRow(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(40))
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40))
    credibility_score: Mapped[float] = mapped_column(Float)
    retrieved_at: Mapped[str] = mapped_column(String(40))


class EvidenceRow(Base):
    __tablename__ = "evidences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str] = mapped_column(String(40))
    competitor_name: Mapped[str] = mapped_column(String(200))
    dimension: Mapped[str] = mapped_column(String(80))
    claim: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    extracted_at: Mapped[str] = mapped_column(String(40))
```

### 14.2 app/infra/db/session.py

```python
"""SQLAlchemy session。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infra.db.models import Base


def build_engine(db_url: str):
    """创建 engine 并初始化表。"""
    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    return engine


def build_session_factory(engine):
    """创建 sessionmaker。"""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
```

### 14.3 app/services/task_service.py

```python
"""任务服务。最外层 try-except,失败写库。"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from app.graph.workflow import build_graph
from app.infra.llm.qwen_dashscope_client import get_token_usage, reset_token_ctx

logger = logging.getLogger(__name__)


class TaskService:
    """任务生命周期管理。"""

    def __init__(self, container, session_factory):
        self.container = container
        self.session_factory = session_factory
        self.graph = build_graph(container)
        self._tasks: dict[str, dict] = {}

    async def create_task(self, query: str, competitors: list[str], dimensions: list[str]) -> str:
        """创建任务并异步启动。

        create_task 必须是 async,避免在无事件循环环境里调用 asyncio.create_task 报错。
        """
        task_id = "task_" + uuid.uuid4().hex[:12]
        from app.infra.db.models import Task
        with self.session_factory() as s:
            s.add(Task(
                id=task_id,
                query=query,
                status="PENDING",
                current_stage=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ))
            s.commit()
        self._tasks[task_id] = {"status": "PENDING", "stage": None, "issues": []}
        asyncio.create_task(self._run(task_id, query, competitors, dimensions))
        return task_id

    async def _run(self, task_id: str, query: str, competitors: list[str], dimensions: list[str]) -> None:
        """执行任务。"""
        try:
            reset_token_ctx()
            self._update_status(task_id, "RUNNING", "planner", [])
            initial_state = {
                "task_id": task_id,
                "task_status": "RUNNING",
                "user_query": query,
                "requested_competitors": competitors,
                "requested_dimensions": dimensions,
                "competitors": [],
                "iteration_count": 0,
                "max_iterations": self.container.settings.max_iterations,
                "sufficiency_threshold": self.container.settings.sufficiency_threshold,
                "issues": [],
                "token_usage": {},
            }
            final = await self.graph.ainvoke(initial_state)
            final["token_usage"] = get_token_usage()
            self._persist(task_id, final)
            self._update_status(
                task_id, final.get("task_status", "COMPLETED"),
                final.get("current_stage", "finalize"), final.get("issues", []),
            )
        except Exception as exc:
            logger.exception("task_failed", extra={"task_id": task_id})
            self._mark_failed(task_id, str(exc))

    def _persist(self, task_id: str, state: dict) -> None:
        """持久化报告、来源与证据。"""
        from app.infra.db.models import EvidenceRow, Report, SourceRow, Task
        with self.session_factory() as s:
            t = s.get(Task, task_id)
            if t:
                t.status = state.get("task_status", "COMPLETED")
                t.current_stage = state.get("current_stage")
                t.finished_at = datetime.utcnow()
                t.updated_at = datetime.utcnow()
            s.add(Report(
                task_id=task_id,
                draft_report=state.get("draft_report"),
                final_report=state.get("final_report"),
                quality_metrics_json=json.dumps(state.get("quality_metrics", {}), ensure_ascii=False),
            ))
            for c in state.get("competitors", []):
                for src in c.get("sources", []):
                    s.add(SourceRow(task_id=task_id, **src))
                for ev in c.get("evidences", []):
                    s.add(EvidenceRow(task_id=task_id, **ev))
            s.commit()

    def _update_status(self, task_id: str, status: str, stage: str | None, issues: list) -> None:
        """更新内存与数据库状态。"""
        from app.infra.db.models import Task
        self._tasks[task_id] = {"status": status, "stage": stage, "issues": issues}
        with self.session_factory() as s:
            t = s.get(Task, task_id)
            if t:
                t.status = status
                t.current_stage = stage
                t.updated_at = datetime.utcnow()
                s.commit()

    def _mark_failed(self, task_id: str, msg: str) -> None:
        """标记失败。"""
        from app.infra.db.models import Task
        with self.session_factory() as s:
            t = s.get(Task, task_id)
            if t:
                t.status = "FAILED"
                t.error_message = msg
                t.updated_at = datetime.utcnow()
                s.commit()
        self._tasks[task_id] = {"status": "FAILED", "stage": "failed", "issues": [msg]}

    def get_status(self, task_id: str) -> dict:
        """查询任务状态。优先内存,不存在时回退 DB。"""
        if task_id in self._tasks:
            return self._tasks[task_id]
        from app.infra.db.models import Task
        with self.session_factory() as s:
            t = s.get(Task, task_id)
            if not t:
                return {"status": "NOT_FOUND"}
            return {"status": t.status, "stage": t.current_stage, "issues": []}

    def get_report(self, task_id: str) -> dict | None:
        """获取报告。"""
        from app.infra.db.models import Report
        with self.session_factory() as s:
            r = s.query(Report).filter_by(task_id=task_id).order_by(Report.id.desc()).first()
            if not r:
                return None
            return {
                "task_id": task_id,
                "report_markdown": r.final_report or r.draft_report or "",
                "quality_metrics": json.loads(r.quality_metrics_json or "{}"),
            }
```

### 14.4 app/api/tasks.py

```python
"""任务相关 API。"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.schemas.report import ReportResponse
from app.schemas.task import CreateTaskRequest, TaskStatusResponse

router = APIRouter(prefix="/api")


def get_task_service(request: Request):
    """从 app.state 获取 TaskService,避免 import app.main 造成循环导入。"""
    return request.app.state.task_service


@router.post("/tasks")
async def create_task(req: CreateTaskRequest, svc=Depends(get_task_service)):
    """创建任务。"""
    task_id = await svc.create_task(req.query, req.competitors, req.dimensions)
    return {"task_id": task_id, "status": "PENDING"}


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str, svc=Depends(get_task_service)):
    """查询任务状态。"""
    info = svc.get_status(task_id)
    if info.get("status") == "NOT_FOUND":
        raise HTTPException(404, "task not found")
    return TaskStatusResponse(
        task_id=task_id,
        status=info["status"],
        current_stage=info.get("stage"),
        progress=0.0,
        issues=[str(i) for i in info.get("issues", [])],
    )


@router.get("/tasks/{task_id}/report", response_model=ReportResponse)
async def get_report(task_id: str, svc=Depends(get_task_service)):
    """获取报告。"""
    rep = svc.get_report(task_id)
    if rep is None:
        raise HTTPException(404, "report not ready")
    info = svc.get_status(task_id)
    return ReportResponse(
        task_id=task_id,
        status=info["status"],
        report_markdown=rep["report_markdown"],
        quality_metrics=rep["quality_metrics"],
    )
```

### 14.5 app/container.py + app/main.py

```python
# app/container.py
"""依赖注入容器。"""

from app.config import Settings
from app.infra.cache.sqlite_cache import SQLiteCache
from app.infra.cache.memory_cache import MemoryCache
from app.infra.llm.qwen_dashscope_client import QwenDashScopeClient
from app.infra.search.service import SearchService
from app.infra.search.tavily import TavilyProvider
from app.infra.search.duckduckgo import DuckDuckGoProvider
from app.infra.fetch.httpx_client import HttpxFetchClient
from app.tools.search_tool import SearchTool
from app.tools.webpage_tool import WebpageTool
from app.tools.extraction_tool import ExtractionTool
from app.tools.source_classifier_tool import SourceClassifierTool
from app.tools.sufficiency_tool import SufficiencyTool
from app.agents.planner import Planner
from app.agents.researcher import Researcher
from app.agents.analyst import Analyst
from app.agents.writer import Writer
from app.agents.critic import Critic


class Container:
    """组件容器。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = (
            SQLiteCache() if settings.cache_backend == "sqlite" else MemoryCache()
        )
        self.llm = QwenDashScopeClient(
            api_key=settings.dashscope_api_key,
            base_url=settings.llm_base_url,
            heavy_model=settings.llm_heavy_model,
            light_model=settings.llm_light_model,
            fallback_model=settings.llm_fallback_model,
        )
        providers = []
        for name in settings.search_providers.split(","):
            name = name.strip()
            if name == "tavily" and settings.tavily_api_key:
                providers.append(TavilyProvider(api_key=settings.tavily_api_key))
            elif name == "duckduckgo":
                providers.append(DuckDuckGoProvider())
        if not providers:
            providers.append(DuckDuckGoProvider())
        self.search_service = SearchService(
            providers, self.cache, settings.max_concurrent_search,
        )
        self.fetch_client = HttpxFetchClient(self.cache)
        self.search_tool = SearchTool(self.search_service)
        self.webpage_tool = WebpageTool(self.fetch_client, self.llm, self.cache)
        self.extraction_tool = ExtractionTool(self.llm)
        self.classifier_tool = SourceClassifierTool(self.llm)
        self.sufficiency_tool = SufficiencyTool()
        self.planner = Planner(self.llm)
        self.researcher = Researcher(
            self.search_tool, self.webpage_tool, self.extraction_tool,
            self.classifier_tool, self.sufficiency_tool,
            threshold=settings.sufficiency_threshold,
            max_rounds=settings.max_search_rounds_per_competitor,
        )
        self.analyst = Analyst(self.llm)
        self.writer = Writer(self.llm)
        self.critic = Critic(self.llm, settings.enable_llm_critic)


# app/main.py
"""FastAPI 入口。"""

from fastapi import FastAPI
from app.config import get_settings
from app.container import Container
from app.infra.db.session import build_engine, build_session_factory
from app.infra.logger import setup_logger
from app.api.tasks import router as tasks_router
from app.services.task_service import TaskService

settings = get_settings()
setup_logger(settings.log_level)
container = Container(settings)
engine = build_engine(settings.db_url)
session_factory = build_session_factory(engine)
task_service = TaskService(container, session_factory)

app = FastAPI(title="InsightAgent")
app.state.task_service = task_service
app.include_router(tasks_router)
```

---

## 15. Commit 13:前端 + E2E + 演示缓存 + 文档

### 15.1 frontend/streamlit_app.py

```python
"""Streamlit 前端。"""

import time
import streamlit as st
import httpx

API = "http://localhost:8000"
st.set_page_config(page_title="InsightAgent", layout="wide")
st.title("InsightAgent — 多 Agent 竞品分析")

with st.form("query_form"):
    query = st.text_input("赛道/产品方向", "AI 编程助手赛道")
    competitors = st.text_input("指定竞品(逗号分隔,可空)", "")
    submitted = st.form_submit_button("开始调研")

if submitted:
    with httpx.Client() as c:
        resp = c.post(f"{API}/api/tasks", json={
            "query": query,
            "competitors": [s.strip() for s in competitors.split(",") if s.strip()],
            "dimensions": [],
        })
        task_id = resp.json()["task_id"]
        st.success(f"任务已创建: {task_id}")

    placeholder = st.empty()
    while True:
        with httpx.Client() as c:
            r = c.get(f"{API}/api/tasks/{task_id}").json()
        placeholder.info(f"状态: {r['status']} | 阶段: {r.get('current_stage')}")
        if r["status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}:
            break
        time.sleep(2)

    if r["status"] != "FAILED":
        with httpx.Client() as c:
            rep = c.get(f"{API}/api/tasks/{task_id}/report").json()
        st.markdown(rep["report_markdown"])
        st.json(rep.get("quality_metrics", {}))
    else:
        st.error("任务失败")
```

### 15.2 scripts/preload_demo_cache.py

```python
"""预跑 3-5 个赛道,把搜索/抓取/抽取结果写入缓存。

面试演示前运行一次,演示时缓存命中,单任务 < 30s。
"""

import asyncio
from app.config import get_settings
from app.container import Container
from app.services.task_service import TaskService
from app.infra.db.session import build_engine, build_session_factory


DEMO_QUERIES = [
    "AI 编程助手赛道",
    "向量数据库对比",
    "AI Agent 框架对比",
]


async def main():
    settings = get_settings()
    container = Container(settings)
    engine = build_engine(settings.db_url)
    sf = build_session_factory(engine)
    svc = TaskService(container, sf)

    for q in DEMO_QUERIES:
        print(f"\npreloading: {q}")
        task_id = await svc.create_task(q, [], [])
        # 简单轮询(实际可改为 await)
        while True:
            await asyncio.sleep(3)
            status = svc.get_status(task_id)["status"]
            print(f"  {task_id} {status}")
            if status in {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}:
                break


if __name__ == "__main__":
    asyncio.run(main())
```

### 15.3 tests/e2e/test_smoke.py

```python
"""无联网 E2E 烟囱测试。所有外部调用使用 Fake/Stub。"""

import time
import pytest
from app.graph.workflow import build_graph


@pytest.mark.asyncio
async def test_full_pipeline_with_fixtures(container_with_stubs):
    """端到端跑完整流程。

    禁止 pass / TODO 占位。必须真实构建带 Fake/Stub 的 Container 并运行 LangGraph。

    要求:
    - 总耗时 < 5s
    - final_report 非空
    - 至少 2 个竞品
    - 所有 dimension_analysis 均有 evidence_refs
    - 不访问外网
    """
    started = time.perf_counter()
    graph = build_graph(container_with_stubs)
    final = await graph.ainvoke({
        "task_id": "task_e2e",
        "task_status": "RUNNING",
        "user_query": "AI 编程助手赛道",
        "requested_competitors": [],
        "requested_dimensions": [],
        "competitors": [],
        "iteration_count": 0,
        "max_iterations": 2,
        "sufficiency_threshold": 0.6,
        "issues": [],
        "token_usage": {},
    })
    assert time.perf_counter() - started < 5
    assert final["final_report"].strip()
    assert len(final["competitors"]) >= 2
    assert final["task_status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
```

### 15.4 examples/sample_report.md(占位)

```markdown
# 竞品分析报告:AI 编程助手赛道

> 由 InsightAgent 自动生成于 2025-XX-XX

## 1. 调研概述
...

## 2. 竞品概览
...

(完整示例由 preload_demo_cache.py 跑出后填入)
```

### 15.5 README.md(完整版)

```markdown
# InsightAgent

基于 LangGraph 的多 Agent 竞品分析系统。输入赛道关键词,自动联网调研、抓取证据、生成带引用的对比报告。

## 特性
- 五 Agent 协作:Planner / Researcher / Analyst / Writer / Critic
- 证据链可追溯:报告每条结论绑定 evidence_id
- Critic 质量门控:Rule-based 检查 + 自动回退 + 迭代熔断
- 千问运行时:业务 LLM 锁定通义千问系列
- 模块化:接口层 + 依赖注入 + 架构测试自动验证

## 架构

```
api → services → graph → agents → tools → infra
```

## 快速启动

```bash
cp .env.example .env
# 填入 DASHSCOPE_API_KEY 与 TAVILY_API_KEY
pip install -e ".[dev]"
pytest                                              # 验证骨架
uvicorn app.main:app --reload                       # 启动后端
streamlit run frontend/streamlit_app.py             # 启动前端
```

## 演示说明

冷启动单任务需 5-8 分钟。演示前请运行:

```bash
python scripts/preload_demo_cache.py
```

预置缓存命中后,演示赛道 < 30s 出结果。

## 当前限制
- 搜索结果依赖第三方 Provider,可能波动
- 仅处理公开网页,不访问登录后内容
- LLM Critic 默认关闭,V0 仅启用 Rule-based
- 报告质量受网页内容质量影响

## 测试

```bash
pytest tests/architecture/    # 架构边界
pytest tests/unit/             # 单元测试
pytest tests/integration/      # 工作流集成
pytest tests/e2e/              # 无联网烟囱
```

## 后续规划
- LLM Critic
- MySQL 持久化
- SSE 进度推送
- MCP 工具层标准化
```

### 15.6 Dockerfile / docker-compose.yml

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY app ./app
COPY frontend ./frontend
COPY scripts ./scripts
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./data:/app/data
  frontend:
    build: .
    command: streamlit run frontend/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
    ports: ["8501:8501"]
    env_file: .env
    depends_on: [api]
```

---

## 16. 最终验收 Checklist

执行 `pytest -v` 必须全部通过,且:

```
✓ tests/architecture/ 全绿
  - test_runtime_model_guard 通过
  - test_no_direct_external_imports 通过
  - test_layer_imports 通过
  - test_file_size_limits 通过
  - test_docstrings 通过

✓ tests/unit/ 全绿
✓ tests/integration/ 全绿
✓ tests/e2e/test_smoke.py 无联网 < 5s 通过
✓ tests/integration/ 与 tests/e2e/ 中不得出现 pass / TODO 占位

✓ ruff check app/ tests/ 通过

✓ 真实联网烟囱:
  - python scripts/verify_qwen_api.py 千问稳定
  - python scripts/smoke_search_fetch.py 搜索抓取稳定
  - python scripts/preload_demo_cache.py 演示缓存就绪

✓ 文档:
  - README.md 含架构图、启动方式、演示说明、当前限制
  - examples/sample_report.md 含真实报告样本
  - .env.example 模型默认为千问

✓ 容器:
  - docker compose up 后 api 与 frontend 正常运行
```

每个 Commit 完成后必须运行:

```bash
pytest tests/architecture/ tests/unit/ -v && ruff check app/ tests/
```

通过后才能开始下一个 Commit。

---

## 17. 关键提醒(给 Codex)

```
1. 严格按 Commit 顺序实现,不要跨 Commit 跳跃
2. 每个 Commit 完成后必须跑测试,通过才进入下一 Commit
3. 任何时候发现代码违反 §0.2 禁止行为,立即重构
4. .env.example 的默认模型必须是千问
5. agents/ 目录任何文件出现 import httpx/openai/anthropic/dashscope 立即报错
6. tools/ 互相 import(除 dedup)立即报错
7. ResearchPlan 的 required_fields 必须经过 model_validator 强校验
8. LLMClient 调用必须传 model_role,不准传 model_name
9. 所有 fetch / search / extract 结果必须经过缓存
10. extract 输入 > 2000 字必须直接抛 ValueError,不能截断兜底
11. openai SDK 只能出现在 qwen_dashscope_client.py,且只能作为 DashScope 兼容端点传输层
12. 用户传入 competitors / dimensions 必须进入 Planner prompt,不能丢弃
13. Search/Fetch 缓存 Key 必须包含影响结果的关键参数,失败抓取只短缓存
14. TaskService.create_task 必须是 async,API 中必须 await
```
