"""Optional Ollama hook for tool-call *proposals*.

When ``FACTORYAGENT_OLLAMA_URL`` is set, a local LLM may read a request and
propose ``{"tool": ..., "params": {...}}``. The proposal has no authority:
the agent passes it through exactly the same allowlist + schema validation
as every other route, and any failure (bad JSON, unknown tool, invalid
params, server down) falls back to the deterministic router. Nothing in
the package — including the test suite — requires Ollama to exist.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .errors import FactoryAgentError


class OllamaError(FactoryAgentError):
    """The Ollama hook could not produce a usable proposal."""


def ollama_url():
    return os.environ.get("FACTORYAGENT_OLLAMA_URL") or None


def ollama_model():
    return os.environ.get("FACTORYAGENT_OLLAMA_MODEL", "llama3.1")


_SYSTEM = (
    "You route manufacturing-engineering requests to tools. "
    "Reply with JSON only: {\"tool\": \"<name>\", \"params\": {...}}. "
    "Available tools:\n"
)


def propose_tool_call(request_text, tool_descriptions, url=None, timeout=15):
    """Ask Ollama for a tool-call proposal. Returns (tool, params).

    Raises OllamaError on any transport/format problem; the caller decides
    whether to fall back. Validation is the caller's job (and it always
    happens — see agent.Agent).
    """
    base = (url or ollama_url() or "").rstrip("/")
    if not base:
        raise OllamaError("FACTORYAGENT_OLLAMA_URL is not set")
    catalogue = "\n".join(
        "- %s: %s" % (t["name"], t["summary"]) for t in tool_descriptions)
    payload = {
        "model": ollama_model(),
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": _SYSTEM + catalogue},
            {"role": "user", "content": request_text},
        ],
    }
    req = urllib.request.Request(
        base + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise OllamaError("ollama request failed: %s" % exc) from exc
    content = (body.get("message") or {}).get("content", "")
    try:
        proposal = json.loads(content)
    except ValueError as exc:
        raise OllamaError("ollama reply was not JSON") from exc
    if not isinstance(proposal, dict) or "tool" not in proposal:
        raise OllamaError("ollama reply has no tool field: %r" % (content[:200],))
    params = proposal.get("params") or {}
    if not isinstance(params, dict):
        raise OllamaError("ollama params must be an object")
    return proposal["tool"], params
