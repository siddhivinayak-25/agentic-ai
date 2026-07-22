"""
shell_tool.py
-------------
A single, deliberately narrow "run_bash" tool. Rejects an explicit list of
dangerous tokens (rm, sudo, curl, ...) and always executes with the
workspace as cwd, under a hard timeout. This is a *teaching* sandbox, not
a production-grade jail - see sandbox.py's module docstring for the caveat.
"""
from __future__ import annotations

from server.config import settings
from server.tools.base import Tool, registry
from server.tools.sandbox import check_command_safety, run_subprocess


import os
import platform

def run_bash(command: str) -> dict:
    try:
        check_command_safety(command)
    except Exception as e:  # SandboxViolation
        return {"error": str(e)}

    bash_path = "bash"
    if platform.system() == "Windows":
        git_bash = r"C:\Program Files\Git\bin\bash.exe"
        if os.path.exists(git_bash):
            bash_path = git_bash

    result = run_subprocess([bash_path, "-lc", command], timeout=settings.tool_timeout_seconds)
    return {"command": command, **result}



registry.register(Tool(
    name="run_bash",
    description=(
        "Run a shell command inside the sandboxed workspace directory. "
        "Blocked tokens: rm, sudo, curl, wget, chmod, chown, dd, mkfs, "
        "shutdown, reboot, kill, killall."
    ),
    parameters={
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
    func=run_bash,
))
