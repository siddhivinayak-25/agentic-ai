"""
base.py
-------
Minimal tool-calling framework. Every tool is a small dataclass with a
JSON schema (handed straight to Groq's OpenAI-compatible tool-use API)
and a `func` that implements it. `registry` is the single shared
ToolRegistry every tool module registers itself into on import.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]        # JSON schema for the tool's arguments
    func: Callable[..., dict]         # implementation; must return a JSON-serialisable dict

    def to_groq_spec(self) -> dict:
        """OpenAI/Groq-compatible function-calling spec for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def specs(self) -> list[dict]:
        return [t.to_groq_spec() for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, arguments_json: str) -> dict:
        """Look up `name` and call it with arguments parsed from JSON.
        Never raises - tool/agent errors come back as {"error": ...} so the
        agent loop can keep going and let the model react to the failure.
        """
        if name not in self._tools:
            return {"error": f"Unknown tool '{name}'. Available: {self.names()}"}

        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON arguments for '{name}': {e}"}

        tool = self._tools[name]
        try:
            return tool.func(**args)
        except TypeError as e:
            return {"error": f"Bad arguments for '{name}': {e}"}
        except Exception as e:  # noqa: BLE001 - a tool must never crash the agent loop
            return {"error": f"Tool '{name}' raised {type(e).__name__}: {e}"}


registry = ToolRegistry()
