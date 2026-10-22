"""The tool registry: the allowlist of everything the agent may do.

A tool exists only because it is registered here with a JSON schema.
Anything else — an unknown name from a user, the router, or an LLM
proposal — is rejected with :class:`UnknownToolError`. This registry is
the complete attack surface of the agent.
"""

from __future__ import annotations

from . import tools as _tools
from .errors import UnknownToolError
from .schema import apply_defaults, validate_params


class Tool:
    def __init__(self, name, summary, schema, handler):
        self.name = name
        self.summary = summary
        self.schema = schema
        self.handler = handler

    def describe(self):
        return {"name": self.name, "summary": self.summary,
                "parameters": self.schema}


class Registry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        self._tools[tool.name] = tool
        return tool

    def get(self, name):
        try:
            return self._tools[name]
        except KeyError:
            raise UnknownToolError(
                "tool %r is not in the registry allowlist (%s)"
                % (name, ", ".join(sorted(self._tools))))

    def names(self):
        return sorted(self._tools)

    def describe_all(self):
        return [self._tools[name].describe() for name in self.names()]

    def validate(self, name, params):
        """Validate params for tool ``name`` and fill schema defaults."""
        tool = self.get(name)
        checked = validate_params(tool.schema, params or {})
        return apply_defaults(tool.schema, checked)


_FILE_LIST = {"type": "array", "items": {"type": "string"}}


def build_default_registry():
    registry = Registry()
    registry.register(Tool(
        name="daily_report",
        summary="Aggregate production daily-report CSVs (date, line, product, "
                "planned, actual, defects) into attainment/defect summary.",
        schema={
            "type": "object",
            "properties": {
                "files": dict(_FILE_LIST),
            },
            "required": [],
            "additionalProperties": False,
        },
        handler=_tools.daily_report,
    ))
    registry.register(Tool(
        name="pareto",
        summary="Defect Pareto analysis from a CSV with defect + count "
                "columns: ranked table, cumulative share, 80/20 cut.",
        schema={
            "type": "object",
            "properties": {
                "file": {"type": "string"},
            },
            "required": [],
            "additionalProperties": False,
        },
        handler=_tools.pareto,
    ))
    registry.register(Tool(
        name="report_gen",
        summary="Generate a Markdown engineering report from a title and "
                "sections (text + tables). Writes a file only when the "
                "run is confirmed; otherwise returns a dry-run preview.",
        schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "text": {"type": "string"},
                            "table": {
                                "type": "object",
                                "properties": {
                                    "columns": {"type": "array",
                                                "items": {"type": "string"}},
                                    "rows": {"type": "array",
                                             "items": {"type": "array"}},
                                },
                                "required": ["columns"],
                                "additionalProperties": False,
                            },
                        },
                        "required": ["heading"],
                        "additionalProperties": False,
                    },
                },
                "output": {"type": "string"},
            },
            "required": ["title"],
            "additionalProperties": False,
        },
        handler=_tools.report_gen,
    ))
    registry.register(Tool(
        name="excel_batch",
        summary="Safe batch spreadsheet ops (merge / select_columns / "
                "rename_columns) on CSV/XLSX. Dry-run preview by default; "
                "writes only when the run is confirmed.",
        schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["merge", "select_columns", "rename_columns"],
                },
                "files": dict(_FILE_LIST),
                "columns": {"type": "array", "items": {"type": "string"}},
                "rename": {"type": "object"},
                "output": {"type": "string"},
            },
            "required": ["operation", "files"],
            "additionalProperties": False,
        },
        handler=_tools.excel_batch,
    ))
    return registry
