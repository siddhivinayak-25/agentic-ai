from typing import Any, Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class AgentEvent(BaseModel):
    """Shape of every Server-Sent Event the /api/chat stream emits."""
    type: Literal["thought", "tool_call", "tool_result", "final", "error", "stream_end"]
    data: dict[str, Any]
