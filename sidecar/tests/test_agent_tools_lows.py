"""Pinning tests for the lows-P2-W3 (tools-envelope) register entries.

Each test names the register id it pins in its docstring so a future reader
can trace the fix back to ``vysted-r15-register.json``.
"""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest


def test_no_agent_tools_registry_v0_6_0_module() -> None:
    """R15-CODE-AGENT-028: the pure pass-through module is gone; its body
    lives inline in ``register_v0_6_0_tools`` and the function still runs
    every Phase 6 domain's ``register()``."""
    assert "services.agent_tools.registry_v0_6_0" not in sys.modules
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("services.agent_tools.registry_v0_6_0")

    from services import agent_tools

    agent_tools.reset_for_tests()
    agent_tools.register_v0_5_0_tools()
    agent_tools.register_v0_6_0_tools()
    for tool_id in ("macro_series", "sec_filings_list", "compare_symbols", "research"):
        assert agent_tools.is_registered(tool_id)


def test_reset_for_tests_restores_every_import_time_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-CODE-AGENT-027: reset_for_tests() used to hardcode ``backtest_summary``
    as the only re-registered tool, so a second module-level ``register_tool(...)``
    call anywhere in the package would silently vanish on reset. It now restores
    a snapshot taken at package-import time — generic over however many tools
    that snapshot holds."""
    from services import agent_tools

    async def _fake_handler(args: dict) -> dict:  # noqa: ARG001
        return {"ok": True}

    monkeypatch.setitem(agent_tools._IMPORT_TIME_TOOLS, "fake_import_time_tool", _fake_handler)
    try:
        agent_tools.reset_for_tests()
        assert agent_tools.is_registered("backtest_summary")
        assert agent_tools.is_registered("fake_import_time_tool")
    finally:
        agent_tools._TOOLS.pop("fake_import_time_tool", None)


def test_invoke_tool_wraps_provider_error_with_one_spelling() -> None:
    """R15-CODE-AGENT-014: a handler that lets ``ProviderError`` (or any other
    exception) escape gets it converted to the ``{"ok": False, "error": ...}``
    envelope by ``invoke_tool`` itself, with one spelling — handlers no
    longer hand-copy this try/except."""
    from services import agent_tools
    from services.errors import ProviderError

    async def _raises_provider_error(args: dict) -> dict:  # noqa: ARG001
        raise ProviderError("upstream is down")

    async def _raises_unexpected(args: dict) -> dict:  # noqa: ARG001
        raise ValueError("boom")

    agent_tools.register_tool("_test_provider_error", _raises_provider_error)
    agent_tools.register_tool("_test_unexpected_error", _raises_unexpected)
    try:
        provider_result = asyncio.run(agent_tools.invoke_tool("_test_provider_error", {}))
        unexpected_result = asyncio.run(agent_tools.invoke_tool("_test_unexpected_error", {}))
    finally:
        agent_tools._TOOLS.pop("_test_provider_error", None)
        agent_tools._TOOLS.pop("_test_unexpected_error", None)

    assert provider_result == {"ok": False, "error": "provider error: upstream is down"}
    assert unexpected_result == {"ok": False, "error": "unexpected error: boom"}


def test_news_tool_failure_uses_the_invoke_tool_envelope_not_its_own_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-CODE-AGENT-014: ``news`` used to prefix its own failure message
    with ``"news fetch failed: "`` — one spelling out of four. It now lets
    the exception propagate to ``invoke_tool``, same as every other tool."""
    from services import agent_tools, news_provider
    from services.agent_tools import news_tool

    async def _boom(client: object, symbols: list[str], limit: int) -> list[object]:  # noqa: ARG001
        raise RuntimeError("feed exploded")

    monkeypatch.setattr(news_provider, "fetch_news", _boom)
    news_tool.register()
    try:
        result = asyncio.run(agent_tools.invoke_tool("news", {}))
    finally:
        agent_tools.reset_for_tests()
        agent_tools.register_v0_5_0_tools()
        agent_tools.register_v0_6_0_tools()

    assert result == {"ok": False, "error": "unexpected error: feed exploded"}
