import pytest

from factoryagent.errors import PathEscapeError
from factoryagent.paths import Workspace


def test_resolve_inside(tmp_path):
    ws = Workspace(tmp_path)
    assert ws.resolve("a/b.csv") == (tmp_path / "a" / "b.csv").resolve()


def test_resolve_root_itself(tmp_path):
    ws = Workspace(tmp_path)
    assert ws.resolve(".") == tmp_path.resolve()


@pytest.mark.parametrize("bad", ["../escape.csv", "../../etc/passwd",
                                 "sub/../../escape.csv"])
def test_traversal_rejected(tmp_path, bad):
    ws = Workspace(tmp_path / "root")
    with pytest.raises(PathEscapeError):
        ws.resolve(bad)


def test_absolute_outside_rejected(tmp_path):
    ws = Workspace(tmp_path / "root")
    with pytest.raises(PathEscapeError):
        ws.resolve(str(tmp_path / "outside.csv"))


def test_absolute_inside_accepted(tmp_path):
    ws = Workspace(tmp_path)
    inside = tmp_path / "ok.csv"
    assert ws.resolve(str(inside)) == inside.resolve()


def test_symlink_escape_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    ws = Workspace(root)
    with pytest.raises(PathEscapeError):
        ws.resolve("link/secret.csv")


def test_contains(tmp_path):
    ws = Workspace(tmp_path)
    assert ws.contains("x.csv")
    assert not ws.contains("../x.csv")


def test_glob_csv(tmp_path):
    (tmp_path / "b.csv").write_text("a\n1\n", encoding="utf-8")
    (tmp_path / "a.csv").write_text("a\n1\n", encoding="utf-8")
    (tmp_path / "c.txt").write_text("x", encoding="utf-8")
    ws = Workspace(tmp_path)
    assert [p.name for p in ws.glob_csv()] == ["a.csv", "b.csv"]
