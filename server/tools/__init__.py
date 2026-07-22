"""Import every tool module so their `registry.register(...)` calls execute
exactly once, at import time, then re-export the shared registry."""
from server.tools import file_tools, python_tool, shell_tool  # noqa: F401
from server.tools.base import registry

__all__ = ["registry"]
