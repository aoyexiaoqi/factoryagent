"""The agent core: route -> validate -> execute.

This is the only execution path in the package, used identically by the
CLI and the HTTP API:

1. A request is routed to a tool — by the deterministic router, or by an
   optional LLM proposal when Ollama is configured.
2. The tool name must be in the registry allowlist and the parameters
   must pass the tool's JSON schema. LLM proposals get *no* shortcuts.
3. The tool runs with a ToolContext bound to the workspace root; writes
   require ``confirmed=True`` (dry-run is the default everywhere).
"""

from __future__ import annotations

from . import ollama as _ollama
from .errors import NoRouteError, UnknownToolError, ValidationError
from .paths import Workspace
from .registry import build_default_registry
from .router import route_request
from .tools import ToolContext


class Agent:
    def __init__(self, workspace, registry=None, use_llm=True):
        self.workspace = workspace if isinstance(workspace, Workspace) \
            else Workspace(workspace)
        self.registry = registry or build_default_registry()
        self.use_llm = use_llm

    # ------------------------------------------------------------- public

    def list_tools(self):
        return self.registry.describe_all()

    def call_tool(self, name, params=None, confirmed=False):
        """Execute a registered tool directly (allowlist + schema enforced)."""
        checked = self.registry.validate(name, params or {})
        tool = self.registry.get(name)
        ctx = ToolContext(self.workspace, confirmed=confirmed)
        result = tool.handler(ctx, checked)
        return {
            "tool": name,
            "params": checked,
            "confirmed": bool(confirmed),
            "result": result,
        }

    def run(self, request_text, confirmed=False):
        """Route a natural-language request and execute the matched tool."""
        routed_by = "rules"
        tool_name = None
        params = None
        if self.use_llm and _ollama.ollama_url():
            proposal = self._llm_proposal(request_text)
            if proposal is not None:
                tool_name, params = proposal
                routed_by = "ollama"
        if tool_name is None:
            route = route_request(request_text)  # raises NoRouteError
            tool_name, params = route.tool, route.params
        outcome = self.call_tool(tool_name, params, confirmed=confirmed)
        outcome["request"] = request_text
        outcome["routed_by"] = routed_by
        return outcome

    # ------------------------------------------------------------ internal

    def _llm_proposal(self, request_text):
        """Return a validated (tool, params) from Ollama, or None to fall back.

        Any problem — transport, format, unknown tool, invalid params —
        returns None; the deterministic router then handles the request.
        """
        try:
            tool_name, params = _ollama.propose_tool_call(
                request_text, self.registry.describe_all())
            self.registry.validate(tool_name, params)
        except Exception:
            return None
        return tool_name, params


__all__ = ["Agent", "NoRouteError", "UnknownToolError", "ValidationError"]
