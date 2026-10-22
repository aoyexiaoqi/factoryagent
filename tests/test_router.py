import pytest

from factoryagent.errors import NoRouteError
from factoryagent.router import route_request


@pytest.mark.parametrize("text,tool", [
    ("汇总生产日报 daily.csv", "daily_report"),
    ("汇总昨天的生产日报", "daily_report"),
    ("summarize the production daily report", "daily_report"),
    ("看一下达成率", "daily_report"),
    ("做缺陷帕累托分析 defects.csv", "pareto"),
    ("defect pareto analysis", "pareto"),
    ("不良分析", "pareto"),
    ("合并 a.csv b.csv", "excel_batch"),
    ("merge a.csv b.csv", "excel_batch"),
    ("生成报告 \"周度分析\"", "report_gen"),
    ("write a report", "report_gen"),
])
def test_routes(text, tool):
    assert route_request(text).tool == tool


def test_route_extracts_files():
    route = route_request("汇总生产日报 daily.csv extra.xlsx")
    assert route.params["files"] == ["daily.csv", "extra.xlsx"]


def test_route_pareto_file():
    route = route_request("做缺陷帕累托分析 defects.csv")
    assert route.params["file"] == "defects.csv"


def test_route_excel_operation_merge():
    route = route_request("合并 a.csv b.csv")
    assert route.params["operation"] == "merge"
    assert route.params["files"] == ["a.csv", "b.csv"]


def test_route_excel_operation_rename():
    route = route_request("给 a.csv 改列名")
    assert route.params["operation"] == "rename_columns"


def test_route_excel_operation_select():
    route = route_request("把 a.csv 选列输出")
    assert route.params["operation"] == "select_columns"


def test_route_report_title_from_quotes():
    route = route_request("生成报告 \"周度工艺分析\"")
    assert route.params["title"] == "周度工艺分析"


@pytest.mark.parametrize("text", [
    "", "   ", "今天天气怎么样", "帮我订一张机票",
    "delete all files", "运行 rm -rf /",
])
def test_no_route(text):
    with pytest.raises(NoRouteError):
        route_request(text)
