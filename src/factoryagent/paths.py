"""Workspace path confinement.

Every file a tool touches must live under a configurable workspace root.
``Workspace.resolve`` is the single choke point: it rejects absolute paths
that point elsewhere, ``..`` traversal, and symlink escapes.
"""

from __future__ import annotations

from pathlib import Path

from .errors import PathEscapeError


class Workspace:
    """A directory that bounds all file access for tools."""

    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative):
        """Resolve ``relative`` inside the workspace or raise PathEscapeError.

        ``relative`` may be a str or Path. Absolute inputs are accepted only
        when they already point inside the root.
        """
        candidate = Path(relative).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise PathEscapeError(
                "path %r escapes workspace root %s" % (str(relative), self.root)
            )
        return resolved

    def contains(self, relative):
        """True when ``relative`` resolves inside the workspace."""
        try:
            self.resolve(relative)
        except PathEscapeError:
            return False
        return True

    def glob_csv(self, pattern="*.csv"):
        """Sorted CSV files directly under the root matching ``pattern``."""
        return sorted(p for p in self.root.glob(pattern) if p.is_file())

    def __repr__(self):  # pragma: no cover - trivial
        return "Workspace(%s)" % self.root
