"""Command line interface.

    factoryagent tools [--workspace DIR]
    factoryagent run "汇总昨天的生产日报" --workspace ./data [--yes]
    factoryagent demo [--workspace DIR]

``--yes`` is the explicit confirmation that allows tools to write files;
without it every write is a dry-run preview.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import Agent
from .errors import FactoryAgentError
from .paths import Workspace

_DAILY_SAMPLE = """date,line,product,planned,actual,defects
2026-10-20,L1,Widget-A,500,486,9
2026-10-20,L2,Widget-B,400,352,21
2026-10-20,L3,Widget-A,300,298,4
2026-10-21,L1,Widget-A,500,495,7
2026-10-21,L2,Widget-B,400,361,18
2026-10-21,L3,Widget-C,300,300,2
"""

_DEFECT_SAMPLE = """defect,count
划伤 Scratch,42
尺寸超差 Dimension,35
漏装 Missing part,18
毛刺 Burr,11
标签错误 Label,6
其他 Other,4
"""


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _cmd_tools(args):
    agent = Agent(args.workspace)
    for tool in agent.list_tools():
        print("%s — %s" % (tool["name"], tool["summary"]))
    return 0


def _cmd_run(args):
    agent = Agent(args.workspace)
    outcome = agent.run(args.request, confirmed=args.yes)
    _print(outcome)
    return 0


def _cmd_demo(args):
    ws = Workspace(args.workspace)
    (ws.root / "production_daily.csv").write_text(_DAILY_SAMPLE, encoding="utf-8")
    (ws.root / "defects.csv").write_text(_DEFECT_SAMPLE, encoding="utf-8")
    (ws.root / "extra_a.csv").write_text(
        "id,name,qty\n1,Alpha,10\n2,Beta,20\n", encoding="utf-8")
    (ws.root / "extra_b.csv").write_text(
        "id,name,qty\n3,Gamma,30\n", encoding="utf-8")
    print("== sample data written to %s" % ws.root)
    agent = Agent(ws)

    print("\n== 1) daily_report via router")
    daily = agent.run("汇总生产日报 production_daily.csv")
    _print(daily["result"])

    print("\n== 2) pareto via router")
    pareto = agent.run("做缺陷帕累托分析 defects.csv")
    _print(pareto["result"])

    print("\n== 3) excel_batch dry-run (default: nothing is written)")
    dry = agent.run("合并 extra_a.csv extra_b.csv")
    _print(dry["result"])
    assert not (ws.root / "excel_batch_output.csv").exists()

    print("\n== 4) excel_batch confirmed write")
    done = agent.call_tool(
        "excel_batch",
        {"operation": "merge", "files": ["extra_a.csv", "extra_b.csv"],
         "output": "merged.csv"},
        confirmed=True)
    _print(done["result"])
    print("merged.csv exists:", (ws.root / "merged.csv").exists())

    print("\n== 5) report_gen dry-run, then confirmed write")
    sections = [
        {"heading": "生产达成", "text": "总达成率 %.2f%%，最差产线：%s。"
         % (daily["result"]["totals"]["attainment_rate"] * 100,
            ", ".join(daily["result"]["worst_lines"])),
         "table": {"columns": ["line", "planned", "actual", "attainment_rate"],
                   "rows": [[b["line"], b["planned"], b["actual"],
                             b["attainment_rate"]]
                            for b in daily["result"]["by_line"]]}},
        {"heading": "缺陷帕累托", "text": "关键少数：%s。"
         % ", ".join(pareto["result"]["vital_few"]),
         "table": {"columns": ["defect", "count", "cumulative_share"],
                   "rows": [[r["defect"], r["count"], r["cumulative_share"]]
                            for r in pareto["result"]["rows"]]}},
    ]
    preview = agent.call_tool(
        "report_gen",
        {"title": "生产日报分析报告", "sections": sections,
         "output": "report.md"},
        confirmed=False)
    print("dry_run:", preview["result"].get("dry_run"), "| written:",
          preview["result"]["written"])
    final = agent.call_tool(
        "report_gen",
        {"title": "生产日报分析报告", "sections": sections,
         "output": "report.md"},
        confirmed=True)
    print("written:", final["result"]["written"], "->",
          Path(ws.root, "report.md"))
    print("\nDemo complete. All writes above required explicit confirmation.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="factoryagent",
        description="Offline manufacturing-engineering agent workbench "
                    "(controlled tools only; dry-run by default).")
    parser.add_argument("--demo", action="store_true",
                        help="run the built-in demo and exit")
    sub = parser.add_subparsers(dest="command")

    p_tools = sub.add_parser("tools", help="list registered tools")
    p_tools.add_argument("--workspace", default="./data")
    p_tools.set_defaults(func=_cmd_tools)

    p_run = sub.add_parser("run", help="route a natural-language request")
    p_run.add_argument("request")
    p_run.add_argument("--workspace", default="./data")
    p_run.add_argument("--yes", action="store_true",
                       help="confirm file writes (default is dry-run)")
    p_run.set_defaults(func=_cmd_run)

    p_demo = sub.add_parser("demo", help="create sample data and run all tools")
    p_demo.add_argument("--workspace", default="./factoryagent-demo")
    p_demo.set_defaults(func=_cmd_demo)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.demo:
        args.workspace = "./factoryagent-demo"
        return _cmd_demo(args)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except FactoryAgentError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
