# InsightAgent 前端重设计文档

> 版本: v4.0.0
> 日期: 2026-05-13
> 框架: Streamlit >= 1.37.0
> 约束: 不迁移框架、不增后端、不增模型供应商、不破坏 API contract

---

## 目录

1. [设计背景](#1-设计背景)
2. [设计目标](#2-设计目标)
3. [页面结构与布局](#3-页面结构与布局)
4. [视觉设计系统](#4-视觉设计系统)
5. [文件架构](#5-文件架构)
6. [组件设计](#6-组件设计)
7. [状态管理](#7-状态管理)
8. [数据流](#8-数据流)
9. [轮询策略](#9-轮询策略)
10. [错误处理矩阵](#10-错误处理矩阵)
11. [实现结果](#11-实现结果)
12. [文件清单](#12-文件清单)

---

## 1. 设计背景

### 旧版问题

| 问题 | 描述 | 影响 |
|------|------|------|
| 阻塞式轮询 | `while` 循环 + `time.sleep(2)` 冻结 Streamlit 事件循环 | 轮询期间 UI 无响应 |
| 无状态管理 | 零使用 `st.session_state`，页面刷新丢失所有状态 | 任务无法恢复 |
| 手写 SVG | 雷达图由 Python 字符串拼接生成，无交互 | 无法 hover 查看数据 |
| 无主题 | 使用 Streamlit 默认亮色主题，无任何 CSS 定制 | 视觉单调 |
| 表单无保护 | 提交期间可重复点击，无 disabled 态 | 重复创建任务 |
| 单体文件 | 413 行单文件，UI/逻辑/API 全混在一起 | 难以维护和测试 |

### 设计约束

- **不移框架** — 保持 Streamlit，不迁移到 React/Vue/Next.js
- **不增后端** — 零后端 API 变更
- **不增模型供应商** — 保持 DeepSeek-only
- **不引入中间件** — 无 Redis/Celery/Kafka/PostgreSQL
- **不破坏 API contract** — 三个端点 (POST /api/tasks, GET /api/tasks/{id}, GET /api/tasks/{id}/report) 完全不变
- **不调用外部 API** — 不调用真实 DeepSeek、Tavily 或网页抓取

---

## 2. 设计目标

1. **非阻塞轮询**: `@st.fragment(run_every=2.0)` 替代 `while True + time.sleep(2)`
2. **状态持久化**: `st.session_state` + `st.query_params["task_id"]` URL 恢复
3. **交互式雷达图**: Plotly `Scatterpolar` 替代手写 SVG
4. **专业 Dashboard 风格**: 暗色主题、卡片式布局、品牌色 #6C63FF
5. **错误韧性**: 连续 5 次失败自动停止轮询，429/503 自动重试
6. **模块化架构**: utils (纯逻辑) / components (Streamlit 渲染) / theme (CSS)

---

## 3. 页面结构与布局

```
+--------------------------------------------------------------------+
| :mag: InsightAgent  Competitive Analysis         :green_circle: Connected |
+--------------------------------------------------------------------+
|           |                                                         |
|  SIDEBAR  |  MAIN CONTENT                                          |
|           |                                                         |
|  History  |  [IDLE]  NO TASK                                       |
|  - task_1 |    +--- centered column ---+                           |
|  - task_2 |    | New Analysis Form     |                           |
|  About    |    | Query [...]           |                           |
|  Check    |    | Competitors [...]     |                           |
|  Conn.    |    | Dimensions [...]      |                           |
|           |    | [Start Research]      |                           |
|           |    +-----------------------+                           |
|           |                                                         |
|           |  [RUNNING] TASK ACTIVE                                  |
|           |    +-- left col --+  +-- right col (fragment) -------+ |
|           |    | Form (compact)|  | :arrows_counterclockwise:      | |
|           |    | [New Task]    |  | Researcher — RUNNING          | |
|           |    +---------------+  | [=========>         ] 45%    | |
|           |                       | Pipeline Stages:              | |
|           |                       | :check: Queued                | |
|           |                       | :blue_circle: Researching     | |
|           |                       | :white_circle: Analyze ...    | |
|           |                       | Issues (2) [expand]           | |
|           |                       +-------------------------------+ |
|           |                                                         |
|           |  [COMPLETED] REPORT READY                               |
|           |    +-- left col --+  +-- right col ------------------+ |
|           |    | Form (enabled)|  | :check: Research completed   | |
|           |    | [New Task]    |  | [Download Markdown]           | |
|           |    +---------------+  |                               | |
|           |                       | [Report] [Coverage] [Quality] | |
|           |                       | [Evidence]                     | |
|           |                       |                               | |
|           |                       | Report markdown...             | |
|           |                       | OR Plotly radar chart          | |
|           |                       | OR Quality metrics JSON        | |
|           |                       +-------------------------------+ |
+--------------------------------------------------------------------+
```

### 三态路由

页面根据 `st.session_state.task_id` 和 `st.session_state.task_completed` 呈现三种状态:

| 状态 | 条件 | 左侧 | 右侧 |
|------|------|------|------|
| **IDLE** | `task_id is None` | 居中表单 | — |
| **RUNNING** | `task_id` 存在, `task_completed == False` | 精简表单 + "New Task" | `st.status()` 进度面板 (fragment 自动轮询) |
| **COMPLETED** | `task_completed == True` | 表单恢复可用 | Report 4-tab 查看器 |

---

## 4. 视觉设计系统

### 配色方案

| Token | 色值 | 用途 |
|-------|------|------|
| `PRIMARY` | `#6C63FF` | 主色调, 按钮, 进度条, Tab 指示器 |
| `PRIMARY_LIGHT` | `#8B83FF` | 按钮 hover 态 |
| `BG_DARK` | `#0E1117` | 页面背景 |
| `BG_CARD` | `#1E2130` | 卡片/容器背景 |
| `BG_SIDEBAR` | `#161922` | 侧边栏背景 |
| `TEXT_PRIMARY` | `#FAFAFA` | 主要文本 |
| `TEXT_SECONDARY` | `#9DA3B4` | 次要文本, Metric 标签 |
| `SUCCESS` | `#22C55E` | 成功状态 |
| `WARNING` | `#F59E0B` | 警告状态 |
| `ERROR` | `#EF4444` | 错误状态 |
| `BORDER` | `#2A2D3A` | 卡片/容器边框 |

### 主题配置

**文件:** `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#6C63FF"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1E2130"
textColor = "#FAFAFA"
font = "sans serif"
```

### CSS 定制

**文件:** `frontend/theme.py`

自定义 CSS 覆盖范围:
- Brand header (渐变标题栏 + 下边框)
- 健康状态徽章
- 卡片容器 (`data-testid="stContainer"`) — 圆角 10px, 边框
- 侧边栏 (`data-testid="stSidebar"`) — 深色背景
- Metric 卡片 (`data-testid="stMetric"`) — 圆角卡片风格
- 进度条 (`data-testid="stProgress"`) — 主色填充
- Tab 切换 (`data-baseweb="tab"`) — 选中态主色高亮
- 按钮 (`kind="primary"`) — 品牌色渐变
- 滚动条 — 细窄暗色
- Expander / Toast / Alert / DataEditor — 统一圆角风格

---

## 5. 文件架构

### 目录结构

```
frontend/
    streamlit_app.py          ← 薄编排层 (~185 行)
    theme.py                  ← CSS 注入 + 色值常量
    utils.py                  ← API helpers, session_state, 格式化, SVG fallback
    components/
        task_form.py          ← 任务创建表单
        status_panel.py       ← @st.fragment 轮询 + st.status() 进度
        coverage_charts.py    ← Plotly 雷达图 + 指标卡片
        report_viewer.py      ← 4-tab 报告查看器
        evidence_viewer.py    ← (不变) 证据引用解析

.streamlit/
    config.toml               ← 主题配置

tests/unit/
    test_streamlit_frontend.py ← (更新) import 路径迁移到 utils
```

### 分层原则

```
streamlit_app.py         ← 编排 + 路由 (imports streamlit + components)
    ↓
components/*.py          ← Streamlit 渲染 (imports streamlit + utils)
    ↓
utils.py                 ← 纯逻辑, 零 Streamlit import 在函数体之外
theme.py                 ← CSS 注入 (imports streamlit)
```

- `utils.py` 可脱离 Streamlit 运行时进行单元测试 (test_streamlit_frontend.py 已验证)
- `components/` 各模块互不依赖, 可独立开发
- `streamlit_app.py` 仅做编排, 不包含业务逻辑

---

## 6. 组件设计

### 6.1 Task Form (`task_form.py`)

```python
render_task_form() -> dict | None
```

**Props (via session_state):**
- `form_disabled: bool` — 控制所有输入和按钮的 disabled 状态
- `task_id: str | None` — 控制 "New Task" 按钮可见性

**特性:**
- 3 个输入: Query (必填), Competitors (可选), Dimensions (可选)
- 内联验证: query >= 2 字符
- Submit 按钮在验证通过前 disabled
- 任务进行中所有输入 disabled (防重复提交)
- "New Task" 按钮: 清除状态并 rerun

**状态处理:**

| 状态 | 视觉 | 交互 |
|------|------|------|
| 无输入 | 占位符, Submit disabled | 用户输入 query |
| 输入不足 | 提示 "at least 2 characters" | 继续输入 |
| 就绪 | Submit 亮起 | 点击提交 |
| 任务进行中 | 全部 disabled | 等待或点 "New Task" |
| 429 错误 | 错误: "at capacity, wait 30s" | 等待重试 |
| 422 错误 | 错误: 显示 validation detail | 修正输入 |
| 网络错误 | 错误: "Failed to create task: ..." | 检查连接 |

### 6.2 Status Panel (`status_panel.py`)

```python
@st.fragment(run_every=2.0)
poll_status_fragment() -> None
```

**Props (via session_state):**
- `task_id`, `task_completed`, `polling_active` — 守卫条件
- `consecutive_failures` — 错误计数
- 写入: `task_status`, `current_stage`, `last_status`, `report_data`, `last_error`

**特性:**
- 每 2 秒自动执行一次 (由 Streamlit 事件循环管理)
- 使用 `st.status()` 展示进度 (可展开/折叠)
- 进度条 + 3 列指标 (Status / Stage / ETA)
- Pipeline 阶段清单 (已完成 :white_check_mark: / 进行中 :blue_circle: / 待处理 :white_circle:)
- Issues 折叠面板

**Fragment 生命周期:**
1. 守卫检查: `task_id` 存在 + 未完成 + polling_active → 继续
2. HTTP 轮询: `GET /api/tasks/{task_id}`
3. 更新 `session_state`
4. 渲染 `st.status()` UI
5. 若终态 (COMPLETED/FAILED): 获取 report, `st.toast()`, `st.rerun()`
6. 若 429/503: 静默返回, fragment 自动重试
7. 若连续 5 次失败: 停止轮询, 显示警告

### 6.3 Coverage Charts (`coverage_charts.py`)

```python
render_coverage_tab(quality_metrics: dict) -> None
```

**特性:**
- 4 列指标卡片: Coverage Score / Sufficient Dimensions / Total Evidence / Missing Dimensions
- **Plotly 交互式雷达图** (主方案):
  - `go.Scatterpolar()` 填充区域
  - 平均值参考线 (虚线)
  - 暗色主题配色
  - Hover tooltip: 维度名 + 证据数
  - 图例水平放置于图表下方
- **SVG 降级方案** (fallback): 若 `plotly` 未安装, 自动使用 `_radar_svg()`
- 可展开的数据表格: Dimension / Evidence Count / Status

**Plotly vs SVG 对比:**

| 特性 | Plotly | SVG (旧) |
|------|--------|----------|
| Hover 交互 | :white_check_mark: | :x: |
| 缩放/平移 | :white_check_mark: | :x: |
| 自定义 tooltip | :white_check_mark: | :x: |
| 响应式 | :white_check_mark: | :x: |
| 离线可用 | :white_check_mark: | :white_check_mark: |
| 依赖大小 | ~15MB | 0 |
| 降级方案 | — | 作为 fallback |

### 6.4 Report Viewer (`report_viewer.py`)

```python
render_report_view(report: dict) -> None
```

**4 个 Tab:**

| Tab | 内容 | 空状态 |
|-----|------|--------|
| **Report** | Markdown 全文渲染 | "No report content was generated." |
| **Coverage** | Plotly 雷达图 + 指标卡片 | "No coverage metrics are available for this report." |
| **Quality Data** | Citation Summary (3 指标) + Missing Refs 警告 + Raw JSON expander | 0 citations, empty JSON |
| **Evidence** | Evidence ID / Source URL / Relevance 表格 | "No evidence records in this report." |

**额外特性:**
- 成功横幅 + Download Markdown 按钮 (Tab 上方)
- 引用缺失警告 (带 ID 列表)
- `st.dataframe()` 可排序证据表格

---

## 7. 状态管理

### Session State Keys

| Key | 类型 | 设置方 | 消费方 | 用途 |
|-----|------|--------|--------|------|
| `task_id` | `str \| None` | `_handle_submit()`, `init_session_state()` (URL 恢复) | `poll_status_fragment()`, 路由守卫 | 当前任务 ID |
| `task_status` | `str \| None` | `poll_status_fragment()` | 报告渲染 | 最新状态字符串 |
| `task_completed` | `bool` | `poll_status_fragment()` | `main()` 布局切换 | 是否为终态 |
| `current_stage` | `str \| None` | `poll_status_fragment()` | 展示 | 当前 Pipeline 阶段 |
| `report_data` | `dict \| None` | `poll_status_fragment()` | `render_report_view()` | 缓存报告 |
| `last_status` | `dict \| None` | `poll_status_fragment()` | 错误恢复 | 最新 API 状态 |
| `polling_active` | `bool` | `_handle_submit()`, `poll_status_fragment()` | Fragment 守卫 | 是否应继续轮询 |
| `last_error` | `str \| None` | `poll_status_fragment()`, `_handle_submit()` | 错误展示 | 持久化错误信息 |
| `consecutive_failures` | `int` | `poll_status_fragment()` | 退避逻辑 | 连续失败计数 |
| `task_history` | `list[dict]` | `_handle_submit()` | Sidebar | 会话任务历史 |
| `health_status` | `dict \| None` | 健康检查按钮 | Header Badge | API 连接状态 |
| `health_checked` | `bool` | `init_session_state()` | 健康检查 | 是否已检查 |
| `report_retry_count` | `int` | — | 报告重试 | 重试计数器 |

### URL 持久化

- `st.query_params["task_id"]` 在任务创建时设置
- 页面刷新时 `init_session_state()` 从 URL 恢复 `task_id`
- `clear_task_state()` 清除 URL 参数

---

## 8. 数据流

```
[用户填写表单] → render_task_form()
       ↓
   返回 {query, competitors, dimensions}
       ↓
[_handle_submit()] → api_create_task() → POST /api/tasks
       ↓
   st.session_state.task_id = task_id
   st.session_state.polling_active = True
   st.query_params["task_id"] = task_id
   st.rerun()
       ↓
[main() rerun] → 看到 task_id 已设置 → _render_active_state()
   ├─ 左侧: render_task_form() (表单可用)
   └─ 右侧: poll_status_fragment()
              │
              ├─ [每 2 秒] → api_get_status(task_id) → GET /api/tasks/{task_id}
              │    └─ _render_status_ui() → st.status() + 进度条 + 阶段清单
              │
              └─ [检测到终态] → api_get_report_with_retries(task_id) → GET /api/tasks/{task_id}/report
                   └─ st.session_state.report_data = report
                   └─ st.toast("Research completed!") → st.rerun()
                          ↓
                   [main() rerun] → 看到 task_completed=True
                       ├─ 左侧: render_task_form() (恢复可用, 新任务)
                       └─ 右侧: render_report_view(report_data)
                            └─ 4 tabs: Report / Coverage / Quality Data / Evidence
```

---

## 9. 轮询策略

### 架构对比

**旧版 (阻塞式):**
```
Streamlit rerun → while True:
    time.sleep(2)         ← 阻塞 Streamlit 事件循环!
    api_get_status()
    if terminal: break
```
- UI 在循环期间完全冻结
- 无法取消
- 无法交互

**新版 (非阻塞):**
```
Streamlit rerun → 渲染 Fragment 占位符
    ↓
[Streamlit 事件循环管理]
    ↓
每 2 秒: Fragment 重新执行
    ├─ 守卫检查 (0ms)
    ├─ HTTP 轮询 (~50ms)
    ├─ 更新 session_state
    ├─ 重渲染 st.status()
    └─ 若终态: st.toast() + st.rerun()
```
- Fragment 之间 UI 完全响应
- 用户可操作表单、Sidebar
- 可随时点 "New Task" 重置

### 错误处理策略

| 异常类型 | 响应 | 重试 | 停止条件 |
|----------|------|------|----------|
| 429 (Rate Limit) | Warning "busy, retrying..." | 自动 (fragment 继续) | — |
| 503 (Unavailable) | Warning "busy, retrying..." | 自动 (fragment 继续) | — |
| Timeout / ConnectError | Warning "connection issue" | 自动 (fragment 继续) | 连续 5 次 |
| 404 (Not Found) | Error, 停止轮询 | 不重试 | 立即 |
| 其他 HTTPError | Error, 计数 | 自动 (fragment 继续) | 连续 5 次 |
| Unexpected Error | Error, 停止轮询 | 不重试 | 立即 |

---

## 10. 错误处理矩阵

| 组件 | 状态 | 视觉 | 用户操作 |
|------|------|------|----------|
| **Task Form** | 无输入 | 占位符, Submit disabled | 输入 query |
| **Task Form** | 输入不足 | 提示文字 | 继续输入 |
| **Task Form** | 429 错误 | 红色错误: "at capacity, wait 30s" | 等待 |
| **Task Form** | 422 错误 | 红色错误 + 验证详情 | 修正输入 |
| **Task Form** | 网络错误 | 红色错误 | 检查连接 |
| **Status Panel** | PENDING | st.status "Queued", 0% 进度 | 等待 |
| **Status Panel** | RUNNING | st.status 当前阶段高亮, 进度条, ETA | 等待或 New Task |
| **Status Panel** | 瞬态错误 | Warning "busy, retrying..." | 等待自动重试 |
| **Status Panel** | 连续 5 次失败 | Warning + 停止轮询 | New Task |
| **Status Panel** | 404 | Error "Task not found" | New Task |
| **Status Panel** | COMPLETED | Toast "Research completed!" → 报告 | 浏览报告 |
| **Status Panel** | FAILED | Toast "Task failed", 错误信息 | New Task |
| **Report** | 未就绪 | "Try Again" 按钮 | 点击重试 |
| **Report** | 空内容 | "No report content was generated." | 重启任务 |
| **Report** | 正常 | 4-tab 显示 | 浏览/下载 |
| **Coverage** | 空数据 | "No coverage metrics available" | 查看其他 Tab |
| **Evidence** | 空记录 | "No evidence records" | 查看其他 Tab |
| **Sidebar** | 无历史 | "No previous tasks" | 提交首个任务 |
| **Sidebar** | 有历史 | 可滚动列表 + Restore 按钮 | 点击恢复 |
| **Header** | 已连接 | :green_circle: Connected | — |
| **Header** | 降级 | :orange_circle: Degraded | 检查 API |
| **Header** | 离线 | :black_circle: Offline | 启动 API 服务 |

---

## 11. 实现结果

### 测试结果

```
platform win32 -- Python 3.12.9
174 passed in 11.19s
```

- 所有现有测试通过, 零回归
- 6 个前端专项测试全部通过
- 前端所有模块 import 验证通过
- 语法检查通过

### 代码规模

| 文件 | 行数 | 类型 |
|------|------|------|
| `streamlit_app.py` | ~185 | 编排层 |
| `theme.py` | ~90 | CSS 注入 |
| `utils.py` | ~260 | 纯逻辑 + API helpers |
| `task_form.py` | ~65 | 表单组件 |
| `status_panel.py` | ~115 | Fragment 轮询 |
| `coverage_charts.py` | ~110 | Plotly 雷达图 |
| `report_viewer.py` | ~90 | 报告查看器 |
| `evidence_viewer.py` | ~50 | (不变) |
| **总计** | **~965** | 7 个模块 |

### 对比旧版

| 指标 | 旧版 | 新版 |
|------|------|------|
| 文件数 | 2 | 10 |
| 总行数 | ~460 | ~965 |
| 单文件最大行数 | 413 | ~260 |
| 阻塞式轮询 | `while + sleep` | `@st.fragment` |
| 状态管理 | 无 | 14 个 session_state key |
| 主题 | 默认亮色 | 暗色 + 自定义 CSS |
| 雷达图 | 手写 SVG | Plotly (SVG fallback) |
| 模块化 | 单体 | 分层 (编排/组件/工具) |
| 测试覆盖 | 6 tests | 6 tests (兼容) |

---

## 12. 文件清单

### 新增文件

| 文件 | 用途 |
|------|------|
| `.streamlit/config.toml` | 暗色主题基础配置 |
| `frontend/theme.py` | CSS 注入 + 品牌色定义 |
| `frontend/utils.py` | API helpers, session_state 初始化, 格式化, SVG fallback |
| `frontend/components/task_form.py` | 带验证的表单组件 |
| `frontend/components/status_panel.py` | Fragment 轮询 + st.status() 进度 |
| `frontend/components/coverage_charts.py` | Plotly 交互式雷达图 |
| `frontend/components/report_viewer.py` | 4-tab 报告查看器 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `frontend/streamlit_app.py` | 从 413 行单体重写为 ~185 行编排层 |
| `pyproject.toml` | 添加 `plotly>=5.18.0`, `pandas>=2.0.0` |
| `tests/unit/test_streamlit_frontend.py` | import 路径从 `frontend.streamlit_app` → `frontend.utils` |

### 未修改文件

| 文件 | 说明 |
|------|------|
| `frontend/components/evidence_viewer.py` | 证据引用解析, 无需改动 |
| `app/api/tasks.py` | API contract 不变 |
| `app/schemas/task.py` | Schema 不变 |
| `app/schemas/report.py` | Schema 不变 |
| `docker-compose.yml` | 不变 |
| `Dockerfile` | 不变 |

---

## 附录: 启动方式

```bash
# 安装依赖
pip install -e .[dev]

# 启动 API (另一个终端)
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 启动前端
streamlit run frontend/streamlit_app.py

# 运行测试
python -m pytest tests/ -v
```
