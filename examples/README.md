# Examples

Sample data used by the quick-start and the demo:

- `production_daily.csv` — two days of production daily reports for three
  lines (columns: date, line, product, planned, actual, defects).
- `defects.csv` — one week of defect counts for Pareto analysis
  (columns: defect, count).

Copy them into a workspace and try:

```bash
mkdir data && cp *.csv data/
factoryagent run "汇总生产日报 production_daily.csv" --workspace ./data
factoryagent run "做缺陷帕累托分析 defects.csv" --workspace ./data
```

All data is fictional and sanitized.
