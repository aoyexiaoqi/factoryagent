from factoryagent.cli import main


def test_cli_tools(ws, capsys):
    assert main(["tools", "--workspace", str(ws.root)]) == 0
    out = capsys.readouterr().out
    assert "daily_report" in out and "pareto" in out


def test_cli_run(ws, capsys):
    assert main(["run", "汇总生产日报 daily.csv",
                 "--workspace", str(ws.root)]) == 0
    out = capsys.readouterr().out
    assert '"tool": "daily_report"' in out


def test_cli_run_no_route_returns_1(ws, capsys):
    assert main(["run", "讲个笑话", "--workspace", str(ws.root)]) == 1
    assert "error" in capsys.readouterr().err


def test_cli_no_command_returns_2(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_cli_demo_subcommand(tmp_path, capsys):
    target = tmp_path / "demo"
    assert main(["demo", "--workspace", str(target)]) == 0
    out = capsys.readouterr().out
    assert "Demo complete" in out
    assert (target / "merged.csv").exists()
    assert (target / "report.md").exists()


def test_cli_demo_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["--demo"]) == 0
    assert (tmp_path / "factoryagent-demo" / "report.md").exists()
