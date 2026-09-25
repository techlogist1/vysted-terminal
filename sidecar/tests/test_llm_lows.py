"""LLM adapter-layer pins for the R15 lows (contract/typing/config threading)."""

from __future__ import annotations

import inspect

from services.llm.base import LLMProvider


def test_stream_chat_abc_is_not_a_coroutine_function() -> None:
    """R15-CODE-PLATFORM-044: every adapter is an async generator and every
    caller does ``async for`` without ``await``, so the ABC must not declare a
    coroutine."""
    assert not inspect.iscoroutinefunction(LLMProvider.stream_chat)
