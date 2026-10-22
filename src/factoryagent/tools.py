"""The controlled tool implementations.

Every tool is a plain Python function with a fixed signature
``handler(ctx, params) -> dict``. Tools receive a :class:`ToolContext`
carrying the workspace (all paths are resolved through it) and the
``confirmed`` flag: tools that write files must refuse to write unless
``ctx.confirmed`` is true, and report a dry-run preview instead.
"""

from __future__ import annotations

from .errors import ToolExecutionError
from .tables import read_table, to_number, write_table

DAILY_COLUMNS = ["date", "line", "product", "planned", "actual", "defects"]

# Chinese header aliases accepted by the pareto tool.
_DEFECT_ALIASES = {"缺陷": "defect", "缺陷类型": "defect", "不良类型": "defect",
                   "不良项目": "defect", "defect_type": "defect"}
_COUNT_ALIASES = {"数量": "count", "不良数": "count", "件数": "count",
                  "次数": "count", "qty": "count"}


class ToolContext:
    """Runtime context handed to every tool (never user-controlled)."""

    def __init__(self, workspace, confirmed=False):
        self.workspace = workspace
        self.confirmed = bool(confirmed)


# ---------------------------------------------------------------- daily report

def _find_daily_files(ctx, files):
    if files:
        return [ctx.workspace.resolve(f) for f in files]
    found = []
    for candidate in ctx.workspace.glob_csv():
        try:
            columns, _rows = read_table(candidate)
        except ToolExecutionError:
            continue
        if set(DAILY_COLUMNS).issubset({c.lower() for c in columns}):
            found.append(candidate)
    if not found:
        raise ToolExecutionError(
            "no daily-report CSV found in workspace (need columns: %s)"
            % ", ".join(DAILY_COLUMNS))
    return found


def daily_report(ctx, params):
    """Aggregate production daily-report CSVs into a summary."""
    paths = _find_daily_files(ctx, params.get("files"))
    by_line = {}
    dates = set()
    total_planned = total_actual = total_defects = 0.0
    for path in paths:
        columns, rows = read_table(path)
        lower = {c.lower(): c for c in columns}
        missing = [c for c in DAILY_COLUMNS if c not in lower]
        if missing:
            raise ToolExecutionError(
                "%s is missing daily-report columns: %s" % (path.name, missing))
        for row in rows:
            line = str(row[lower["line"]])
            planned = to_number(row[lower["planned"]])
            actual = to_number(row[lower["actual"]])
            defects = to_number(row[lower["defects"]])
            dates.add(str(row[lower["date"]]))
            bucket = by_line.setdefault(
                line, {"line": line, "planned": 0.0, "actual": 0.0,
                       "defects": 0.0})
            bucket["planned"] += planned
            bucket["actual"] += actual
            bucket["defects"] += defects
            total_planned += planned
            total_actual += actual
            total_defects += defects
    lines = []
    for bucket in by_line.values():
        planned = bucket["planned"]
        actual = bucket["actual"]
        bucket = dict(bucket)
        bucket["attainment_rate"] = round(actual / planned, 4) if planned else 0.0
        bucket["defect_rate"] = round(bucket["defects"] / actual, 4) if actual else 0.0
        bucket["planned"] = int(planned) if planned == int(planned) else planned
        bucket["actual"] = int(actual) if actual == int(actual) else actual
        bucket["defects"] = int(bucket["defects"]) if bucket["defects"] == int(bucket["defects"]) else bucket["defects"]
        lines.append(bucket)
    lines.sort(key=lambda b: (b["attainment_rate"], b["line"]))
    return {
        "files": [p.name for p in paths],
        "dates": sorted(dates),
        "totals": {
            "planned": int(total_planned) if total_planned == int(total_planned) else total_planned,
            "actual": int(total_actual) if total_actual == int(total_actual) else total_actual,
            "defects": int(total_defects) if total_defects == int(total_defects) else total_defects,
            "attainment_rate": round(total_actual / total_planned, 4) if total_planned else 0.0,
            "defect_rate": round(total_defects / total_actual, 4) if total_actual else 0.0,
        },
        "by_line": lines,
        "worst_lines": [b["line"] for b in lines[:3]],
    }


# ---------------------------------------------------------------------- pareto

def _normalise_pareto_columns(columns):
    mapping = {}
    for col in columns:
        low = col.lower()
        if low == "defect" or col in _DEFECT_ALIASES:
            mapping[col] = "defect"
        elif low == "count" or col in _COUNT_ALIASES:
            mapping[col] = "count"
    return mapping


def pareto(ctx, params):
    """Defect Pareto analysis: ranked table with cumulative share."""
    file_param = params.get("file")
    if file_param:
        path = ctx.workspace.resolve(file_param)
    else:
        path = None
        for candidate in ctx.workspace.glob_csv():
            try:
                columns, _rows = read_table(candidate)
            except ToolExecutionError:
                continue
            if len(_normalise_pareto_columns(columns)) == 2:
                path = candidate
                break
        if path is None:
            raise ToolExecutionError(
                "no pareto CSV found in workspace (need defect + count columns)")
    columns, rows = read_table(path)
    mapping = _normalise_pareto_columns(columns)
    if len(mapping) != 2:
        raise ToolExecutionError(
            "%s needs a defect column and a count column" % path.name)
    defect_col = next(c for c, v in mapping.items() if v == "defect")
    count_col = next(c for c, v in mapping.items() if v == "count")
    totals = {}
    for row in rows:
        name = str(row[defect_col]).strip()
        if not name:
            continue
        totals[name] = totals.get(name, 0.0) + to_number(row[count_col])
    grand = sum(totals.values())
    if grand <= 0:
        raise ToolExecutionError("%s has no positive defect counts" % path.name)
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    table = []
    cumulative = 0.0
    crossed = False
    for rank, (name, count) in enumerate(ranked, start=1):
        share = count / grand
        cumulative += share
        within = not crossed
        if cumulative >= 0.8:
            crossed = True
        table.append({
            "rank": rank,
            "defect": name,
            "count": int(count) if count == int(count) else count,
            "share": round(share, 4),
            "cumulative_share": round(cumulative, 4),
            "in_vital_few": within,
        })
    return {
        "file": path.name,
        "total_defects": int(grand) if grand == int(grand) else grand,
        "rows": table,
        "vital_few": [r["defect"] for r in table if r["in_vital_few"]],
    }


# ------------------------------------------------------------------ report gen

def _render_markdown(title, sections):
    out = ["# %s" % title, ""]
    for section in sections:
        heading = section.get("heading", "")
        if heading:
            out.append("## %s" % heading)
            out.append("")
        text = section.get("text")
        if text:
            out.append(str(text))
            out.append("")
        table = section.get("table")
        if table:
            cols = [str(c) for c in table.get("columns", [])]
            if cols:
                out.append("| " + " | ".join(cols) + " |")
                out.append("| " + " | ".join("---" for _ in cols) + " |")
                for row in table.get("rows", []):
                    cells = [str(row[i]) if i < len(row) else "" for i in range(len(cols))]
                    out.append("| " + " | ".join(cells) + " |")
                out.append("")
    return "\n".join(out).rstrip() + "\n"


def report_gen(ctx, params):
    """Render a Markdown engineering report; write it only when confirmed."""
    title = params["title"]
    sections = params.get("sections", [])
    content = _render_markdown(title, sections)
    result = {"title": title, "content": content, "written": False}
    output = params.get("output")
    if output:
        target = ctx.workspace.resolve(output)
        result["output"] = str(target.relative_to(ctx.workspace.root))
        if ctx.confirmed:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            result["written"] = True
        else:
            result["dry_run"] = True
            result["note"] = "dry-run: report not written; re-run with confirmation to write %s" % output
    return result


# ----------------------------------------------------------------- excel batch

def excel_batch(ctx, params):
    """Safe batch spreadsheet ops on CSV/XLSX with dry-run by default."""
    operation = params["operation"]
    files = params.get("files") or []
    if not files:
        raise ToolExecutionError("excel_batch needs at least one input file")
    paths = [ctx.workspace.resolve(f) for f in files]
    columns = None
    rows = []
    for path in paths:
        cols, file_rows = read_table(path)
        if columns is None:
            columns = list(cols)
        else:
            for col in cols:
                if col not in columns:
                    columns.append(col)
        rows.extend(file_rows)
    if operation == "select_columns":
        wanted = params.get("columns") or []
        missing = [c for c in wanted if c not in columns]
        if missing:
            raise ToolExecutionError("columns not found: %s" % missing)
        rows = [{c: row.get(c, "") for c in wanted} for row in rows]
        columns = list(wanted)
    elif operation == "rename_columns":
        rename = params.get("rename") or {}
        missing = [c for c in rename if c not in columns]
        if missing:
            raise ToolExecutionError("columns not found: %s" % missing)
        original_columns = columns
        columns = [rename.get(c, c) for c in original_columns]
        rows = [{rename.get(c, c): row.get(c, "") for c in original_columns}
                for row in rows]
    output = params.get("output") or "excel_batch_output.csv"
    target = ctx.workspace.resolve(output)
    result = {
        "operation": operation,
        "inputs": [p.name for p in paths],
        "output": str(target.relative_to(ctx.workspace.root)),
        "columns": columns,
        "row_count": len(rows),
        "preview": [{c: row.get(c, "") for c in columns} for row in rows[:5]],
        "written": False,
    }
    if ctx.confirmed:
        write_table(target, columns, rows)
        result["written"] = True
    else:
        result["dry_run"] = True
        result["note"] = "dry-run: nothing written; re-run with confirmation to write %s" % output
    return result
