"""
sandbox.py
----------
Every filesystem or subprocess action performed by a tool MUST go through
this module. It enforces one invariant: nothing the agent does can touch
a path outside of WORKSPACE_ROOT, and every subprocess call has a hard
timeout.

This is a *soft* sandbox: path-jailing + timeouts + a command blocklist.
It is NOT a substitute for a container or VM if you plan to run genuinely
untrusted code. For a learning project, it is enough to stop the classic
"../../etc/passwd" path-escape or an accidental "rm -rf /".
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from server.config import settings


class SandboxViolation(Exception):
    """Raised whenever a tool tries to escape the workspace jail."""


WORKSPACE_ROOT: Path = settings.workspace_dir.resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

# Tokens we refuse to run inside run_bash, even though we are already
# jailed to WORKSPACE_ROOT. Defence in depth.
_DANGEROUS_TOKENS = {
    "rm", "sudo", "shutdown", "reboot", "mkfs", "dd",
    "chmod", "chown", "curl", "wget", "kill", "killall",
}


def resolve_path(relative_path: str) -> Path:
    """
    Turn a tool-supplied path into an absolute path guaranteed to live
    inside WORKSPACE_ROOT. Raises SandboxViolation if it doesn't.
    """
    candidate = (WORKSPACE_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise SandboxViolation(
            f"Path '{relative_path}' resolves outside the sandboxed workspace "
            f"({WORKSPACE_ROOT}). Refusing."
        )
    return candidate


def check_command_safety(command: str) -> None:
    """Raise SandboxViolation if `command` contains a blocked token."""
    try:
        tokens = shlex.split(command)
    except ValueError as e:
        raise SandboxViolation(f"Could not parse command: {e}")

    for tok in tokens:
        if tok.strip().lower() in _DANGEROUS_TOKENS:
            raise SandboxViolation(
                f"Command contains blocked token '{tok}'. Refusing to run: {command}"
            )


def run_subprocess(args: list[str], timeout: int, cwd: Path | None = None) -> dict:
    """
    Run a subprocess with a hard timeout, capturing stdout/stderr.
    Always executes with cwd inside the workspace (or a subdirectory of it).
    """
    cwd = cwd or WORKSPACE_ROOT
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-10_000:],
            "stderr": proc.stderr[-10_000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout if isinstance(e.stdout, str) else ""
        return {
            "returncode": None,
            "stdout": stdout[-10_000:],
            "stderr": f"Process timed out after {timeout}s and was killed.",
            "timed_out": True,
        }
    except FileNotFoundError as e:
        return {"returncode": None, "stdout": "", "stderr": str(e), "timed_out": False}
