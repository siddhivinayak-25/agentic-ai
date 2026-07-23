"""
file_tools.py
-------------
Filesystem tools exposed to the agent:
  - list_dir      : see what's in a folder
  - read_file      : read a file (optionally a line range), line-numbered
  - write_file     : create a file or overwrite it completely
  - edit_file      : replace one exact, unique substring (Claude-Code style)
  - search_files   : grep-like substring search across files

Every path is passed through sandbox.resolve_path() before it is touched.
"""
from __future__ import annotations

from pathlib import Path

from server.tools.base import Tool, registry
from server.tools.sandbox import WORKSPACE_ROOT, resolve_path


def _rel(p: Path) -> str:
    return str(p.relative_to(WORKSPACE_ROOT))


def list_dir(path: str = ".") -> dict:
    target = resolve_path(path)
    if not target.exists():
        return {"error": f"'{path}' does not exist"}
    if not target.is_dir():
        return {"error": f"'{path}' is not a directory"}

    entries = []
    for item in sorted(target.iterdir()):
        entries.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return {"path": path, "entries": entries}


def read_file(path: str, start_line: int | None = None, end_line: int | None = None) -> dict:
    target = resolve_path(path)
    if not target.exists():
        return {"error": f"'{path}' does not exist"}
    if not target.is_file():
        return {"error": f"'{path}' is not a file"}

    lines = target.read_text(errors="replace").splitlines()
    total = len(lines)
    start = max(0, (start_line - 1) if start_line else 0)
    end = min(total, end_line if end_line else total)

    numbered = [f"{i + start + 1:>5}\t{line}" for i, line in enumerate(lines[start:end])]
    return {
        "path": path,
        "total_lines": total,
        "shown_lines": [start + 1, end],
        "content": "\n".join(numbered),
    }


def write_file(path: str, content: str, overwrite: bool = True) -> dict:
    target = resolve_path(path)
    if target.exists() and not overwrite:
        return {"error": f"'{path}' already exists and overwrite=False"}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {"path": path, "bytes_written": len(content.encode()), "status": "ok"}


def edit_file(path: str, old_str: str, new_str: str) -> dict:
    target = resolve_path(path)
    if not target.exists():
        return {"error": f"'{path}' does not exist"}

    text = target.read_text()
    count = text.count(old_str)
    if count == 0:
        return {"error": "old_str was not found in the file. Re-read the file to get exact text."}
    if count > 1:
        return {"error": f"old_str is not unique ({count} occurrences) - include more surrounding context."}

    target.write_text(text.replace(old_str, new_str, 1))
    return {"path": path, "status": "ok", "replacements": 1}


def search_files(pattern: str, path: str = ".", glob: str = "*") -> dict:
    root = resolve_path(path)
    if not root.exists():
        return {"error": f"'{path}' does not exist"}

    matches = []
    for file in root.rglob(glob):
        if not file.is_file():
            continue
        try:
            text = file.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                matches.append({"file": _rel(file), "line": i, "text": line.strip()[:200]})

    return {"pattern": pattern, "matches": matches[:200], "total_matches": len(matches)}


def delete_file(path: str) -> dict:
    target = resolve_path(path)
    if not target.exists():
        return {"error": f"'{path}' does not exist"}
    
    try:
        if target.is_dir():
            target.rmdir()
            return {"path": path, "status": "ok", "message": "Directory deleted successfully"}
        else:
            target.unlink()
            return {"path": path, "status": "ok", "message": "File deleted successfully"}
    except Exception as e:
        return {"error": f"Failed to delete '{path}': {e}"}


def search_workspace_code(query: str) -> dict:
    try:
        from server.tools.indexing import search_code
        results = search_code(query)
        return {"query": query, "results": results, "status": "ok"}
    except Exception as e:
        return {"error": f"Search query failed: {e}"}


registry.register(Tool(
    name="list_dir",
    description="List files and folders inside a directory of the sandboxed workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path relative to workspace root. Defaults to '.'"},
        },
    },
    func=list_dir,
))

registry.register(Tool(
    name="read_file",
    description="Read a text file from the workspace, optionally a line range. Returns line-numbered content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer", "description": "1-indexed, optional"},
            "end_line": {"type": "integer", "description": "1-indexed inclusive, optional"},
        },
        "required": ["path"],
    },
    func=read_file,
))

registry.register(Tool(
    name="write_file",
    description="Create a new file or completely overwrite an existing file with the given content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "overwrite": {"type": "boolean", "description": "default true"},
        },
        "required": ["path", "content"],
    },
    func=write_file,
))

registry.register(Tool(
    name="edit_file",
    description=(
        "Edit a file by replacing an EXACT, UNIQUE substring (old_str) with new_str. "
        "old_str must match exactly once - include enough surrounding context to make "
        "it unique. Safer than write_file for small, targeted changes."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_str": {"type": "string"},
            "new_str": {"type": "string"},
        },
        "required": ["path", "old_str", "new_str"],
    },
    func=edit_file,
))

registry.register(Tool(
    name="search_files",
    description="Grep-like search for a plain-text substring across files under a directory.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "default '.'"},
            "glob": {"type": "string", "description": "filename glob filter, e.g. '*.py'. default '*'"},
        },
        "required": ["pattern"],
    },
    func=search_files,
))

registry.register(Tool(
    name="delete_file",
    description="Delete a file or an empty folder inside the sandboxed workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to delete relative to workspace root"},
        },
        "required": ["path"],
    },
    func=delete_file,
))

registry.register(Tool(
    name="search_workspace_code",
    description="Search code snippets inside the workspace using fast full-text indexing (FTS5). Returns ranked line ranges.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or keyword"},
        },
        "required": ["query"],
    },
    func=search_workspace_code,
))

