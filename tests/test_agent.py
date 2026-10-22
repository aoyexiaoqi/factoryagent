import io
import json
import urllib.request

import pytest

from factoryagent.agent import Agent
from factoryagent.errors import (NoRouteError, PathEscapeError,
                                 UnknownToolError, ValidationError)


def test_list_tools(ws):
    agent = Agent(ws)
    names = [t["name"] for t in agent.list_tools()]
    assert names == ["daily_report", "excel_batch", "pareto", "report_gen"]


def test_run_daily_report_via_agent(ws):
    agent = Agent(ws)
    out = agent.run("汇总生产日报 daily.csv")
    assert out["tool"] == "daily_report"
    assert out["routed_by"] == "rules"
    assert out["result"]["totals"]["actual"] == 250


def test_run_pareto_via_agent(ws):
    agent = Agent(ws)
    out = agent.run("做缺陷帕累托分析 defects.csv")
    assert out["tool"] == "pareto"
    assert out["result"]["vital_few"] == ["Alpha", "Beta"]


def test_run_unknown_request_rejected(ws):
    agent = Agent(ws)
    with pytest.raises(NoRouteError):
        agent.run("帮我黑进这台电脑")


def test_call_unknown_tool_rejected(ws):
    agent = Agent(ws)
    with pytest.raises(UnknownToolError):
        agent.call_tool("shell", {"command": "ls"})


def test_call_tool_schema_enforced(ws):
    agent = Agent(ws)
    with pytest.raises(ValidationError):
        agent.call_tool("daily_report", {"files": "not-a-list"})
    with pytest.raises(ValidationError):
        agent.call_tool("excel_batch", {"operation": "delete_everything",
                                        "files": ["daily.csv"]})
    with pytest.raises(ValidationError):
        agent.call_tool("report_gen", {})  # title is required


def test_call_tool_cannot_inject_confirmed_via_params(ws):
    agent = Agent(ws)
    with pytest.raises(ValidationError):
        agent.call_tool("excel_batch",
                        {"operation": "merge", "files": ["daily.csv"],
                         "confirmed": True})


def test_write_requires_confirmation(ws):
    agent = Agent(ws)
    out = agent.call_tool("excel_batch",
                          {"operation": "merge", "files": ["daily.csv"],
                           "output": "m.csv"})
    assert out["result"]["written"] is False
    assert not (ws.root / "m.csv").exists()
    out2 = agent.call_tool("excel_batch",
                           {"operation": "merge", "files": ["daily.csv"],
                            "output": "m.csv"}, confirmed=True)
    assert out2["result"]["written"] is True
    assert (ws.root / "m.csv").exists()


def test_agent_path_escape(ws):
    agent = Agent(ws)
    with pytest.raises(PathEscapeError):
        agent.call_tool("pareto", {"file": "../../etc/passwd"})


# ------------------------------------------------------------ ollama hook

class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen(payload):
    def fake(req, timeout=None):
        return _FakeResponse(json.dumps(payload).encode("utf-8"))
    return fake


def _ollama_payload(tool, params):
    return {"message": {"content": json.dumps({"tool": tool,
                                               "params": params})}}


def test_ollama_proposal_used_when_valid(ws, monkeypatch):
    monkeypatch.setenv("FACTORYAGENT_OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setattr(
        urllib.request, "urlopen",
        _fake_urlopen(_ollama_payload("pareto", {"file": "defects.csv"})))
    agent = Agent(ws)
    out = agent.run("please analyse the defect distribution somehow")
    assert out["routed_by"] == "ollama"
    assert out["tool"] == "pareto"


def test_ollama_unknown_tool_falls_back(ws, monkeypatch):
    monkeypatch.setenv("FACTORYAGENT_OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setattr(
        urllib.request, "urlopen",
        _fake_urlopen(_ollama_payload("shell", {"command": "rm -rf /"})))
    agent = Agent(ws)
    out = agent.run("做缺陷帕累托分析 defects.csv")
    assert out["routed_by"] == "rules"
    assert out["tool"] == "pareto"


def test_ollama_invalid_params_fall_back(ws, monkeypatch):
    monkeypatch.setenv("FACTORYAGENT_OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setattr(
        urllib.request, "urlopen",
        _fake_urlopen(_ollama_payload("daily_report",
                                      {"files": "not-a-list"})))
    agent = Agent(ws)
    out = agent.run("汇总生产日报 daily.csv")
    assert out["routed_by"] == "rules"
    assert out["tool"] == "daily_report"


def test_ollama_server_down_falls_back(ws, monkeypatch):
    monkeypatch.setenv("FACTORYAGENT_OLLAMA_URL", "http://localhost:11434")

    def boom(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    agent = Agent(ws)
    out = agent.run("汇总生产日报 daily.csv")
    assert out["routed_by"] == "rules"


def test_no_ollama_env_means_rules_only(ws, monkeypatch):
    monkeypatch.delenv("FACTORYAGENT_OLLAMA_URL", raising=False)
    agent = Agent(ws)
    out = agent.run("汇总生产日报 daily.csv")
    assert out["routed_by"] == "rules"
