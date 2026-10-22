import pytest

from factoryagent.paths import Workspace

DAILY_CSV = """date,line,product,planned,actual,defects
2026-10-21,L1,Widget-A,100,90,5
2026-10-21,L2,Widget-B,100,60,10
2026-10-22,L1,Widget-A,100,100,2
"""

PARETO_CSV = """defect,count
Alpha,50
Beta,30
Gamma,15
Delta,5
"""

PARETO_CN_CSV = """缺陷,数量
划伤,10
毛刺,5
"""


@pytest.fixture()
def ws(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    (root / "daily.csv").write_text(DAILY_CSV, encoding="utf-8")
    (root / "defects.csv").write_text(PARETO_CSV, encoding="utf-8")
    return Workspace(root)


@pytest.fixture()
def daily_only(tmp_path):
    root = tmp_path / "only"
    root.mkdir()
    (root / "daily.csv").write_text(DAILY_CSV, encoding="utf-8")
    return Workspace(root)
