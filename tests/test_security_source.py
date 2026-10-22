"""Static guarantees: the package must not contain execution primitives.

These tests scan the shipped source so a future change cannot quietly
introduce a shell/eval escape hatch.
"""

from pathlib import Path

import factoryagent

FORBIDDEN = ["subprocess", "os.system", "os.popen", "shell=True",
             "eval(", "exec(", "__import__", "pickle.loads"]


def _sources():
    root = Path(factoryagent.__file__).parent
    return sorted(root.rglob("*.py"))


def test_no_execution_primitives_in_source():
    offenders = []
    for path in _sources():
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                offenders.append("%s contains %r" % (path.name, token))
    assert offenders == []


def test_registry_is_the_whole_surface():
    from factoryagent.registry import build_default_registry
    registry = build_default_registry()
    assert registry.names() == ["daily_report", "excel_batch",
                                "pareto", "report_gen"]
