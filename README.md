# FactoryAgent

**离线制造工程 AI Agent 工作台** — 自然语言只能触发*经过授权的受控工具*，永不执行任意命令。

FactoryAgent 面向制造业工艺 / IE 工程师：你说一句「汇总昨天的生产日报」或「做一份缺陷帕累托分析」，系统把它路由到注册表中的某个工具，经 JSON Schema 校验参数后执行。工具集是封闭的白名单，文件访问被限制在工作区目录内，所有写文件操作默认 **dry-run 预览**，必须显式确认才真正落盘。整个系统可完全离线运行；可选的 Ollama 接入只允许本地大模型*提议*工具调用，提议仍须通过同一套白名单 + Schema 校验，校验不过自动回退到确定性规则路由。

## 工具集（V1）

| 工具 | 功能 |
|---|---|
| `daily_report` | 汇总生产日报 CSV（date, line, product, planned, actual, defects）→ 达成率、缺陷率、产线排名、最差产线 |
| `pareto` | 缺陷帕累托分析（defect, count，支持中文列名）→ 排序表、累计占比、80/20 关键少数标注 |
| `report_gen` | 由标题 + 章节（文本/表格）生成 Markdown 工程报告（写文件需确认） |
| `excel_batch` | CSV/XLSX 安全批量处理：合并 / 选列 / 改列名，默认 dry-run 预览，确认后才写 |

## 快速开始

```bash
pip install -e .            # 离线环境可先在有网机器下载 wheel 再安装
factoryagent tools          # 查看工具白名单
factoryagent demo           # 内置演示：样例数据 → 四个工具全跑一遍（含 dry-run → 确认写）

mkdir data && cp examples/*.csv data/
factoryagent run "汇总生产日报 production_daily.csv" --workspace ./data
factoryagent run "做缺陷帕累托分析 defects.csv" --workspace ./data
factoryagent run "合并 a.csv b.csv" --workspace ./data            # dry-run 预览
factoryagent run "合并 a.csv b.csv" --workspace ./data --yes      # 确认后写文件
```

## HTTP API

```bash
pip install -e .[serve]
FACTORYAGENT_WORKSPACE=./data uvicorn factoryagent.app:app --port 8000
curl localhost:8000/tools
curl -X POST localhost:8000/run -H 'Content-Type: application/json' \
     -d '{"request": "做缺陷帕累托分析 defects.csv", "confirmed": false}'
```

CLI 与 API 共用同一条执行路径（路由 → 白名单 → Schema 校验 → 路径限制 → 执行）。

## 安全模型（摘要）

- **没有任意执行**：代码中不存在 shell / `eval` / 动态导入；无法匹配到注册工具的请求直接拒绝。
- **白名单 + Schema**：工具名必须在注册表中，参数必须通过其 JSON Schema（未知参数、类型错误、枚举外的值全部拒绝）。
- **路径沙箱**：所有文件路径经 `Workspace.resolve` 解析，`..` 穿越、指向工作区外的绝对路径、符号链接逃逸一律拒绝。
- **写需确认**：默认 dry-run；CLI 要 `--yes`，API 要 `"confirmed": true`，才允许写文件。
- **LLM 无特权**：Ollama 提议与规则路由走完全相同的校验；提议非法时静默回退规则路由。

详见 [docs/security.md](docs/security.md) 与 [docs/usage.md](docs/usage.md)。

## 可选：Ollama

```bash
export FACTORYAGENT_OLLAMA_URL=http://localhost:11434
export FACTORYAGENT_OLLAMA_MODEL=llama3.1   # 可选
```

设置后，自然语言请求先由本地模型提议工具调用；不设置则使用确定性关键词路由（中英文）。任何情况下都不依赖外部网络。

## 开发

```bash
pip install -e .[dev]
pytest --cov=factoryagent
```

MIT License.

---

## English

**FactoryAgent** is an offline manufacturing-engineering agent workbench. Natural language can only trigger *authorized, controlled tools* — never arbitrary commands.

Requests (Chinese or English) are routed to a fixed registry of tools, parameters are validated against JSON schemas, all file access is confined to a workspace root, and every write is a dry-run preview unless explicitly confirmed. An optional Ollama hook lets a local LLM *propose* tool calls, but proposals must pass the same allowlist + schema validation, with automatic fallback to the deterministic router.

Tools in V1: `daily_report` (production daily-report aggregation), `pareto` (defect Pareto analysis with the 80/20 cut), `report_gen` (Markdown engineering reports), `excel_batch` (safe CSV/XLSX merge / select / rename, dry-run by default).

```bash
pip install -e .
factoryagent demo
factoryagent run "summarize the production daily report" --workspace ./data
```

See [docs/security.md](docs/security.md) for the security model. MIT License.
