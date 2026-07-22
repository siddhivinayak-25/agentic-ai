"""
python_tool.py
--------------
Lets the agent execute Python: either a file already in the workspace, or
a throwaway snippet it wants to test something with. Both run through
sandbox.run_subprocess (hard timeout, workspace-only cwd), using the same
interpreter the server itself runs on.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from server.config import settings
from server.tools.base import Tool, registry
from server.tools.sandbox import resolve_path, run_subprocess


def run_python_file(path: str, args: list[str] | None = None) -> dict:
    target = resolve_path(path)
    if not target.exists():
        return {"error": f"'{path}' does not exist"}

    cmd = [sys.executable, str(target), *(args or [])]
    result = run_subprocess(cmd, timeout=settings.tool_timeout_seconds, cwd=target.parent)
    return {"path": path, **result}


def run_python_code(code: str) -> dict:
    """Run a throwaway snippet without needing to create a permanent file first."""
    tmp_dir = resolve_path(".agent_tmp")
    tmp_dir.mkdir(exist_ok=True)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", dir=tmp_dir, delete=False) as f:
        f.write(code)
        tmp_path = Path(f.name)

    try:
        cmd = [sys.executable, str(tmp_path)]
        return run_subprocess(cmd, timeout=settings.tool_timeout_seconds, cwd=tmp_dir)
    finally:
        tmp_path.unlink(missing_ok=True)


registry.register(Tool(
    name="run_python_file",
    description="Execute a Python file that already exists in the workspace and return stdout/stderr/returncode.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "args": {"type": "array", "items": {"type": "string"}, "description": "optional CLI arguments"},
        },
        "required": ["path"],
    },
    func=run_python_file,
))

registry.register(Tool(
    name="run_python_code",
    description="Execute a short Python code snippet directly, without creating a file first. Good for quick checks/calculations.",
    parameters={
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    },
    func=run_python_code,
))
