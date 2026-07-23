from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from server.agent.loop import run_agent
from server.agent.schemas import ChatRequest
from server.tools.sandbox import resolve_path, WORKSPACE_ROOT, SandboxViolation

router = APIRouter()


def _sse_format(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/chat")
def chat(req: ChatRequest):
    history = [m.model_dump() for m in req.history]

    def event_stream():
        for event in run_agent(req.message, history):
            yield _sse_format(event)
        yield _sse_format({"type": "stream_end", "data": {}})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/workspace/files")
def workspace_files(path: str = "."):
    try:
        target = resolve_path(path)
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"Path '{path}' does not exist")
        if not target.is_dir():
            raise HTTPException(status_code=400, detail=f"Path '{path}' is not a directory")

        entries = []
        for item in sorted(target.iterdir()):
            rel_path = str(item.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "path": rel_path
            })
        return {"path": path, "entries": entries}
    except SandboxViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/file")
def workspace_file(path: str):
    try:
        target = resolve_path(path)
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"File '{path}' does not exist")
        if not target.is_file():
            raise HTTPException(status_code=400, detail=f"Path '{path}' is not a file")

        content = target.read_text(encoding="utf-8", errors="replace")
        rel_path = str(target.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
        return {
            "path": rel_path,
            "content": content,
            "size": target.stat().st_size
        }
    except SandboxViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

