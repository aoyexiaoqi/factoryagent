"""Minimal tabular IO helpers (CSV via stdlib, XLSX via openpyxl).

A table is a ``(columns, rows)`` pair: a list of column names and a list of
row dicts. Keeping one internal representation lets the tools stay
format-agnostic.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .errors import ToolExecutionError


def read_table(path):
    """Read a CSV or XLSX file into ``(columns, rows)``."""
    path = Path(path)
    if not path.is_file():
        raise ToolExecutionError("file not found: %s" % path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(path)
    if suffix in (".xlsx", ".xlsm"):
        return _read_xlsx(path)
    raise ToolExecutionError("unsupported table format: %s" % path.suffix)


def write_table(path, columns, rows):
    """Write ``(columns, rows)`` to a CSV or XLSX file. Returns the Path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        _write_csv(path, columns, rows)
    elif suffix in (".xlsx", ".xlsm"):
        _write_xlsx(path, columns, rows)
    else:
        raise ToolExecutionError("unsupported table format: %s" % path.suffix)
    return path


def _read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ToolExecutionError("empty CSV (no header): %s" % path)
        columns = [c.strip() for c in reader.fieldnames]
        rows = []
        for raw in reader:
            row = {}
            for col in columns:
                value = raw.get(col)
                row[col] = value.strip() if isinstance(value, str) else value
            rows.append(row)
    return columns, rows


def _write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _read_xlsx(path):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ToolExecutionError("openpyxl is required for XLSX files") from exc
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            raise ToolExecutionError("empty XLSX (no header): %s" % path)
        columns = [str(c).strip() if c is not None else "" for c in header]
        rows = []
        for values in rows_iter:
            if values is None or all(v is None for v in values):
                continue
            row = {}
            for col, value in zip(columns, values):
                row[col] = "" if value is None else value
            rows.append(row)
    finally:
        wb.close()
    return columns, rows


def _write_xlsx(path, columns, rows):
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ToolExecutionError("openpyxl is required for XLSX files") from exc
    wb = Workbook()
    ws = wb.active
    ws.append(list(columns))
    for row in rows:
        ws.append([row.get(c, "") for c in columns])
    wb.save(path)


def to_number(value, default=0.0):
    """Best-effort numeric coercion used by the analysis tools."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default
