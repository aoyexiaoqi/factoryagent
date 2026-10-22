# Security model / 安全模型

FactoryAgent is designed for engineers who (rightly) do not trust an "AI
agent" with their files. The design rule is: **the model proposes, the
registry disposes.** This document states exactly what the agent can and
cannot do.

## What the agent can do

Only the tools registered in `factoryagent/registry.py`:

| Tool | Reads | Writes |
|---|---|---|
| `daily_report` | CSVs inside the workspace | nothing |
| `pareto` | one CSV inside the workspace | nothing |
| `report_gen` | nothing | one Markdown file inside the workspace, **only when confirmed** |
| `excel_batch` | CSV/XLSX inside the workspace | one CSV/XLSX inside the workspace, **only when confirmed** |

That is the complete list. There is no tool for deleting files, moving
files, running programs, or accessing the network.

## Enforcement layers

1. **Allowlist** — `Registry.get` raises `UnknownToolError` for any tool
   name that was not registered. Router output and LLM proposals alike go
   through it.
2. **Schema validation** — every call's parameters are validated against
   the tool's JSON schema (`factoryagent/schema.py`): required fields,
   types, enums; unknown parameters are rejected.
3. **Path confinement** — every path a tool touches is resolved through
   `Workspace.resolve`, which rejects `..` traversal, absolute paths
   outside the root, and symlink escapes (`PathEscapeError`).
4. **Write confirmation** — tools that write check the runtime
   `confirmed` flag, which user parameters cannot set: it comes only from
   the CLI `--yes` flag or the API's top-level `confirmed` field. The
   default everywhere is dry-run.
5. **No dynamic execution** — the package contains no `eval`, `exec`,
   `subprocess`, `os.system`, or dynamic importing of user input. The
   test suite asserts these primitives are absent from the source.

## The Ollama hook

With `FACTORYAGENT_OLLAMA_URL` set, a local LLM may propose a tool call.
The proposal is *data*, not authority: it must name a registered tool and
carry schema-valid parameters, or it is discarded and the deterministic
router handles the request instead. The LLM cannot set `confirmed`, cannot
choose paths outside the workspace, and cannot invent tools.

## Non-goals / limitations

- FactoryAgent is not a sandbox against a malicious *workspace*: if you
  put a hostile CSV in the workspace, tools will read it as data (never
  execute it), but values flow into reports verbatim.
- Confirmation is a UX guardrail, not an authentication mechanism. Put
  the HTTP API behind your own auth if you expose it beyond localhost.
- Symlink checks use `Path.resolve()` on the host filesystem; extremely
  adversarial TOCTOU races are out of scope for a single-user workbench.
