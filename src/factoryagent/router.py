"""Deterministic natural-language router (Chinese + English).

Intent is matched with explicit keyword rules — no model, no network,
fully reproducible. The router only ever *proposes* a registered tool
name plus parameters; the agent still validates the proposal against the
tool schema before anything runs.
"""

from __future__ import annotations

import re

from .errors import NoRouteError

_FILE_RE = re.compile(r"[^\s\"'，、；;]+\.(?:csv|xlsx)", re.IGNORECASE)
_QUOTED_RE = re.compile(r"[\"“「]([^\"”」]+)[\"”」]")


class Route:
    def __init__(self, tool, params, reason):
        self.tool = tool
        self.params = params
        self.reason = reason

    def __repr__(self):  # pragma: no cover - trivial
        return "Route(%s, %s)" % (self.tool, self.params)


def _contains(text, *keywords):
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def _files(text):
    return _FILE_RE.findall(text)


def route_request(text):
    """Map a natural-language request to a Route, or raise NoRouteError."""
    if not text or not text.strip():
        raise NoRouteError("empty request")
    files = _files(text)

    # --- pareto: defect distribution analysis --------------------------
    if _contains(text, "帕累托", "pareto", "缺陷分析", "不良分析",
                 "缺陷分布", "defect analysis", "80/20"):
        params = {}
        if files:
            params["file"] = files[0]
        return Route("pareto", params, "matched pareto/defect keywords")

    # --- excel_batch: merge / select / rename --------------------------
    if _contains(text, "合并", "merge", "改列名", "重命名列", "列重命名",
                 "rename column", "选列", "选择列", "只保留", "select column",
                 "批量处理", "batch"):
        if _contains(text, "改列名", "重命名", "rename"):
            operation = "rename_columns"
        elif _contains(text, "选列", "选择列", "只保留", "select column"):
            operation = "select_columns"
        else:
            operation = "merge"
        params = {"operation": operation, "files": files}
        return Route("excel_batch", params,
                     "matched spreadsheet keywords -> %s" % operation)

    # --- daily_report: production daily reports ------------------------
    if _contains(text, "生产日报", "日报", "daily report",
                 "production report", "达成率", "产量汇总", "生产汇总"):
        params = {}
        if files:
            params["files"] = files
        return Route("daily_report", params, "matched daily-report keywords")

    # --- report_gen: write a report ------------------------------------
    if _contains(text, "生成报告", "写报告", "出报告", "工程报告",
                 "generate report", "write a report", "make a report"):
        quoted = _QUOTED_RE.search(text)
        title = quoted.group(1) if quoted else "工程报告"
        params = {
            "title": title,
            "sections": [{"heading": "概述", "text": text.strip()}],
        }
        return Route("report_gen", params, "matched report keywords")

    raise NoRouteError(
        "no registered tool matches this request; "
        "the agent only runs allowlisted tools")
