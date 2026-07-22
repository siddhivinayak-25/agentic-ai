"""
llm.py
------
Thin wrapper around Groq's OpenAI-compatible chat completions endpoint,
using the official `groq` Python SDK. Kept tiny and isolated so it is the
only file that needs to change if you ever swap providers.
"""
from __future__ import annotations

from groq import Groq

from server.config import settings

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
                "(get one free at https://console.groq.com/keys)."
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def chat_completion(messages: list[dict], tools: list[dict]):
    """One call to the model. Returns the raw Groq ChatCompletion object."""
    client = get_client()
    return client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.2,
        max_tokens=4096,
    )
