import pytest

from factoryagent import tools
from factoryagent.errors import PathEscapeError, ToolExecutionError
from factoryagent.paths import Workspace
from factoryagent.tables import read_table, write_table
from factoryagent.tools import ToolContext


def ctx(ws, confirmed=False):
    return ToolContext(ws, confirmed=confirmed)


# ------------------------------------------------------------- daily_report

def test_daily_report_aggregation(ws):
    result = tools.daily_report(ctx(ws), {"files": ["daily.csv"]})
    totals = result["totals"]
    assert totals["planned"] == 300
    assert totals["actual"] == 250
    assert totals["defects"] == 17
    assert totals["attainment_rate"] == round(250 / 300, 4)
    assert result["dates"] == ["2026-10-21", "2026-10-22"]


def test_daily_report_worst_line(ws):
    result = tools.daily_report(ctx(ws), {"files": ["daily.csv"]})
    assert result["worst_lines"][0] == "L2"
    by_line = {b["line"]: b for b in result["by_line"]}
    assert by_line["L1"]["attainment_rate"] == 0.95
    assert by_line["L2"]["defect_rate"] == round(10 / 60, 4)


def test_daily_report_autodiscovery(daily_only):
    result = tools.daily_report(ctx(daily_only), {})
    assert result["files"] == ["daily.csv"]


def test_daily_report_missing_columns(tmp_path):
    root = tmp_path / "d"
    root.mkdir()
    (root / "bad.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ToolExecutionError):
        tools.daily_report(ctx(Workspace(root)), {"files": ["bad.csv"]})


def test_daily_report_no_files_found(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(ToolExecutionError):
        tools.daily_report(ctx(Workspace(root)), {})


def test_daily_report_path_escape(ws):
    with pytest.raises(PathEscapeError):
        tools.daily_report(ctx(ws), {"files": ["../secret.csv"]})


# ------------------------------------------------------------------- pareto

def test_pareto_ranking_and_cut(ws):
    result = tools.pareto(ctx(ws), {"file": "defects.csv"})
    rows = result["rows"]
    assert [r["defect"] for r in rows] == ["Alpha", "Beta", "Gamma", "Delta"]
    assert rows[0]["share"] == 0.5
    assert rows[1]["cumulative_share"] == 0.8
    assert result["vital_few"] == ["Alpha", "Beta"]
    assert rows[2]["in_vital_few"] is False
    assert result["total_defects"] == 100


def test_pareto_autodiscovery(ws):
    result = tools.pareto(ctx(ws), {})
    assert result["file"] == "defects.csv"


def test_pareto_chinese_headers(tmp_path):
    root = tmp_path / "cn"
    root.mkdir()
    (root / "cn.csv").write_text("缺陷,数量\n划伤,10\n毛刺,5\n",
                                  encoding="utf-8")
    result = tools.pareto(ctx(Workspace(root)), {"file": "cn.csv"})
    assert result["rows"][0]["defect"] == "划伤"
    assert result["total_defects"] == 15


def test_pareto_missing_file(ws):
    with pytest.raises(ToolExecutionError):
        tools.pareto(ctx(ws), {"file": "nope.csv"})


# --------------------------------------------------------------- report_gen

def test_report_gen_renders_markdown(ws):
    result = tools.report_gen(ctx(ws), {
        "title": "周报",
        "sections": [{"heading": "达成", "text": "良好。",
                      "table": {"columns": ["line", "rate"],
                                "rows": [["L1", 0.95]]}}],
    })
    content = result["content"]
    assert content.startswith("# 周报")
    assert "## 达成" in content
    assert "| line | rate |" in content
    assert "| L1 | 0.95 |" in content
    assert result["written"] is False


def test_report_gen_dry_run_does_not_write(ws):
    result = tools.report_gen(ctx(ws, confirmed=False), {
        "title": "T", "sections": [], "output": "out.md"})
    assert result["dry_run"] is True
    assert not (ws.root / "out.md").exists()


def test_report_gen_confirmed_writes(ws):
    result = tools.report_gen(ctx(ws, confirmed=True), {
        "title": "T", "sections": [], "output": "out.md"})
    assert result["written"] is True
    assert (ws.root / "out.md").read_text(encoding="utf-8").startswith("# T")


def test_report_gen_output_escape_rejected(ws):
    with pytest.raises(PathEscapeError):
        tools.report_gen(ctx(ws, confirmed=True), {
            "title": "T", "sections": [], "output": "../evil.md"})


# -------------------------------------------------------------- excel_batch

def _two_files(tmp_path):
    root = tmp_path / "batch"
    root.mkdir()
    write_table(root / "a.csv", ["id", "name"], [{"id": 1, "name": "x"}])
    write_table(root / "b.csv", ["id", "name"], [{"id": 2, "name": "y"}])
    return Workspace(root)


def test_excel_merge_dry_run(tmp_path):
    ws = _two_files(tmp_path)
    result = tools.excel_batch(ctx(ws), {
        "operation": "merge", "files": ["a.csv", "b.csv"],
        "output": "m.csv"})
    assert result["row_count"] == 2
    assert result["dry_run"] is True
    assert not (ws.root / "m.csv").exists()


def test_excel_merge_confirmed(tmp_path):
    ws = _two_files(tmp_path)
    result = tools.excel_batch(ctx(ws, confirmed=True), {
        "operation": "merge", "files": ["a.csv", "b.csv"],
        "output": "m.csv"})
    assert result["written"] is True
    _cols, rows = read_table(ws.root / "m.csv")
    assert len(rows) == 2


def test_excel_select_columns(tmp_path):
    ws = _two_files(tmp_path)
    result = tools.excel_batch(ctx(ws, confirmed=True), {
        "operation": "select_columns", "files": ["a.csv"],
        "columns": ["name"], "output": "s.csv"})
    assert result["columns"] == ["name"]
    cols, _rows = read_table(ws.root / "s.csv")
    assert cols == ["name"]


def test_excel_select_missing_column(tmp_path):
    ws = _two_files(tmp_path)
    with pytest.raises(ToolExecutionError):
        tools.excel_batch(ctx(ws), {
            "operation": "select_columns", "files": ["a.csv"],
            "columns": ["nope"]})


def test_excel_rename_columns(tmp_path):
    ws = _two_files(tmp_path)
    result = tools.excel_batch(ctx(ws, confirmed=True), {
        "operation": "rename_columns", "files": ["a.csv"],
        "rename": {"name": "label"}, "output": "r.csv"})
    assert result["columns"] == ["id", "label"]
    _cols, rows = read_table(ws.root / "r.csv")
    assert rows[0]["label"] == "x"


def test_excel_xlsx_roundtrip(tmp_path):
    root = tmp_path / "xl"
    root.mkdir()
    write_table(root / "in.xlsx", ["id", "v"], [{"id": 1, "v": "a"}])
    ws = Workspace(root)
    result = tools.excel_batch(ctx(ws, confirmed=True), {
        "operation": "merge", "files": ["in.xlsx"], "output": "out.xlsx"})
    assert result["written"] is True
    cols, rows = read_table(root / "out.xlsx")
    assert cols == ["id", "v"]
    assert str(rows[0]["v"]) == "a"


def test_excel_output_escape_rejected(tmp_path):
    ws = _two_files(tmp_path)
    with pytest.raises(PathEscapeError):
        tools.excel_batch(ctx(ws, confirmed=True), {
            "operation": "merge", "files": ["a.csv"],
            "output": "../../evil.csv"})
