"""
FastAPI server for the AI Test Suite Orchestrator.
Endpoints:
  GET  /api/agents                     — list available agents
  POST /api/run                        — start a test run
  GET  /api/run/{run_id}/stream        — SSE event stream
  GET  /api/run/{run_id}/report        — download final markdown report
  GET  /api/run/{run_id}/status        — poll run status
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import re as _re

from orchestrator import AGENT_META, get_agents_list, run_suite


def _resolve_path(raw: str) -> str:
    """
    Accept Windows paths (C:\\... or C:/...) and convert to WSL /mnt/<drive>/...
    Passes through already-valid POSIX paths unchanged.
    """
    raw = raw.strip().strip('"').strip("'")

    # Already a valid absolute POSIX path — return as-is
    if raw.startswith("/"):
        return raw

    # Windows path:  C:\Users\...  or  C:/Users/...
    m = _re.match(r"^([A-Za-z]):[/\\](.*)", raw)
    if m:
        drive = m.group(1).lower()
        rest  = m.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"

    # Relative path — resolve against cwd (best-effort)
    return str(Path(raw).resolve())

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="AI Test Suite Orchestrator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory run store ───────────────────────────────────────────────────────

RUNS: dict[str, dict] = {}


# ── Request models ────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    target: str
    target_type: Literal["url", "path"]
    agents: list[str]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/agents")
async def list_agents():
    return {"agents": get_agents_list()}


@app.post("/api/run")
async def start_run(req: RunRequest):
    if not req.target.strip():
        raise HTTPException(status_code=400, detail="Target cannot be empty.")

    valid_agents = [a for a in req.agents if a in AGENT_META]
    if not valid_agents:
        raise HTTPException(status_code=400, detail="No valid agents selected.")

    if req.target_type == "path":
        resolved = _resolve_path(req.target)
        if not Path(resolved).exists():
            raise HTTPException(
                status_code=400,
                detail=f"Path does not exist: {req.target}"
                       + (f" (tried WSL path: {resolved})" if resolved != req.target else ""),
            )
        req = req.model_copy(update={"target": resolved})

    run_id = uuid.uuid4().hex[:10]
    queue: asyncio.Queue = asyncio.Queue()

    RUNS[run_id] = {
        "status": "running",
        "queue": queue,
        "events": [],
        "report": None,
        "config": req.model_dump(),
    }

    asyncio.create_task(
        run_suite(run_id, req.target, req.target_type, valid_agents, queue, RUNS[run_id])
    )

    return {"run_id": run_id, "agents": valid_agents}


@app.get("/api/run/{run_id}/stream")
async def stream_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found.")

    run = RUNS[run_id]
    queue: asyncio.Queue = run["queue"]

    async def generator():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield {"data": json.dumps(item), "id": run_id}
            if item.get("type") == "stream_end":
                break

    return EventSourceResponse(generator())


@app.get("/api/run/{run_id}/status")
async def run_status(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found.")
    run = RUNS[run_id]
    return {
        "run_id": run_id,
        "status": run["status"],
        "has_report": run["report"] is not None,
        "config": run["config"],
    }


@app.get("/api/run/{run_id}/report")
async def download_report(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found.")
    report = RUNS[run_id].get("report")
    if not report:
        raise HTTPException(status_code=425, detail="Report not ready yet.")
    return Response(
        content=report,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="test-report-{run_id}.md"'},
    )


# ── Serve frontend ────────────────────────────────────────────────────────────

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(Path(__file__).parent))
