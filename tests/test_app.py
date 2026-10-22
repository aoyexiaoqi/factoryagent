import pytest
from fastapi.testclient import TestClient

from factoryagent.app import create_app


@pytest.fixture()
def client(ws):
    return TestClient(create_app(str(ws.root)))


def test_get_tools(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()["tools"]]
    assert "pareto" in names and "daily_report" in names


def test_post_run_daily(client):
    resp = client.post("/run", json={"request": "汇总生产日报 daily.csv"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tool"] == "daily_report"
    assert body["result"]["totals"]["planned"] == 300


def test_post_run_no_route_is_400(client):
    resp = client.post("/run", json={"request": "讲个笑话"})
    assert resp.status_code == 400


def test_post_tool_call_dry_run_default(client, ws):
    resp = client.post("/tools/excel_batch", json={
        "params": {"operation": "merge", "files": ["daily.csv"],
                   "output": "m.csv"}})
    assert resp.status_code == 200
    assert resp.json()["result"]["written"] is False
    assert not (ws.root / "m.csv").exists()


def test_post_tool_call_confirmed(client, ws):
    resp = client.post("/tools/excel_batch", json={
        "params": {"operation": "merge", "files": ["daily.csv"],
                   "output": "m.csv"},
        "confirmed": True})
    assert resp.status_code == 200
    assert resp.json()["result"]["written"] is True
    assert (ws.root / "m.csv").exists()


def test_post_unknown_tool_is_400(client):
    resp = client.post("/tools/shell", json={"params": {}})
    assert resp.status_code == 400


def test_post_run_traversal_is_400(client):
    resp = client.post("/run", json={"request": "做缺陷帕累托分析 ../secret.csv"})
    assert resp.status_code == 400
