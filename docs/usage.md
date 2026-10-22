# Usage / 使用说明

## Concepts

- **Workspace** — a directory that bounds all file access. Pass it with
  `--workspace` (CLI) or `FACTORYAGENT_WORKSPACE` (API). Create it and
  put your CSV/XLSX files inside.
- **Dry-run** — the default for every write. You get a preview (row
  counts, head rows, target path); nothing is written until you confirm
  with `--yes` (CLI) or `"confirmed": true` (API).

## Routing examples (deterministic, 中英文)

| Request | Tool |
|---|---|
| `汇总生产日报 production_daily.csv` | `daily_report` |
| `summarize the production daily report` | `daily_report` |
| `做缺陷帕累托分析 defects.csv` | `pareto` |
| `defect pareto analysis` | `pareto` |
| `合并 a.csv b.csv` | `excel_batch` (merge) |
| `merge a.csv b.csv` | `excel_batch` (merge) |
| `给 report.csv 改列名` | `excel_batch` (rename_columns) |
| `生成报告 "周度工艺分析"` | `report_gen` |

When a request names no file, `daily_report` auto-discovers CSVs whose
header contains `date, line, product, planned, actual, defects`, and
`pareto` auto-discovers the first CSV with defect + count columns
(Chinese headers 缺陷/数量 are accepted).

## Data formats

Production daily report CSV:

```csv
date,line,product,planned,actual,defects
2026-10-21,L1,Widget-A,500,486,9
```

Pareto CSV:

```csv
defect,count
划伤 Scratch,42
尺寸超差 Dimension,35
```

`excel_batch` reads and writes CSV and XLSX interchangeably (XLSX via
openpyxl). Merging unions the columns of all inputs.

## Programmatic use

```python
from factoryagent.agent import Agent

agent = Agent("./data")
print(agent.list_tools())
out = agent.run("做缺陷帕累托分析 defects.csv")          # read-only
out = agent.call_tool("excel_batch",
                      {"operation": "merge", "files": ["a.csv", "b.csv"]},
                      confirmed=False)                     # dry-run
```

## Demo

`factoryagent demo` writes sample data to `./factoryagent-demo`, runs all
four tools through the router, and demonstrates the dry-run → confirmed
write flow for both `excel_batch` and `report_gen`.
