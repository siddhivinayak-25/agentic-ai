"""
loop.py
-------
The actual agent loop: THINK -> ACT (call tools) -> OBSERVE -> repeat,
until the model produces a plain-text final answer or we hit
max_agent_iterations.

Implemented as a generator so the API layer can stream every step to the
client the moment it happens (Server-Sent Events) instead of waiting for
the whole run to finish.
"""
from __future__ import annotations

import json
from typing import Any, Iterator

from server.agent.llm import chat_completion
from server.agent.prompts import SYSTEM_PROMPT
from server.config import settings
from server.tools import registry


def run_agent(user_message: str, history: list[dict]) -> Iterator[dict]:
    """Yields dicts of the form {"type": ..., "data": {...}} - see schemas.AgentEvent."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tool_specs = registry.specs()

    for step in range(settings.max_agent_iterations):
        try:
            response = chat_completion(messages, tool_specs)
        except Exception as e:  # noqa: BLE001 - surface any LLM/network error to the client
            yield {"type": "error", "data": {"message": str(e)}}
            return

        choice = response.choices[0]
        msg = choice.message

        assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        if msg.content:
            yield {"type": "thought", "data": {"text": msg.content, "step": step}}

        if not msg.tool_calls:
            # Model gave a plain-text answer with no further tool calls: we're done.
            yield {"type": "final", "data": {"text": msg.content or ""}}
            return

        for tc in msg.tool_calls:
            name = tc.function.name
            args_json = tc.function.arguments

            yield {"type": "tool_call", "data": {"name": name, "arguments": args_json, "step": step}}

            result = registry.execute(name, args_json)

            yield {"type": "tool_result", "data": {"name": name, "result": result, "step": step}}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(result)[:8000],
            })

    yield {
        "type": "error",
        "data": {"message": f"Stopped after {settings.max_agent_iterations} iterations without a final answer."},
    }
