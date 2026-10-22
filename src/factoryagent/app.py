"""FastAPI surface for FactoryAgent.

    GET  /tools  -> the registry allowlist with JSON schemas
    POST /run    -> {"request": "...", "confirmed": false}

The HTTP layer adds nothing of its own: it calls Agent.run, so routing,
allowlist checks, schema validation, path confinement and dry-run
semantics are exactly the CLI's. Start with:

    FACTORYAGENT_WORKSPACE=./data uvicorn factoryagent.app:app
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .agent import Agent
from .errors import FactoryAgentError


class RunRequest(BaseModel):
    request: str = Field(..., description="natural-language request")
    confirmed: bool = Field(
        False, description="must be true to allow tools to write files")


class ToolCallRequest(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


def create_app(workspace: Optional[str] = None) -> FastAPI:
    root = workspace or os.environ.get("FACTORYAGENT_WORKSPACE", "./data")
    agent = Agent(root)
    app = FastAPI(title="FactoryAgent", version="0.1.0",
                  description="Offline manufacturing-engineering agent "
                              "workbench with controlled, allowlisted tools.")

    @app.get("/tools")
    def tools():
        return {"tools": agent.list_tools()}

    @app.post("/run")
    def run(body: RunRequest):
        try:
            return agent.run(body.request, confirmed=body.confirmed)
        except FactoryAgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/tools/{name}")
    def call(name: str, body: ToolCallRequest):
        try:
            return agent.call_tool(name, body.params,
                                   confirmed=body.confirmed)
        except FactoryAgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return app


app = create_app()
