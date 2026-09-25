"""Pinning tests for the lows-P2-W3 (tools-envelope) register entries.

Each test names the register id it pins in its docstring so a future reader
can trace the fix back to ``vysted-r15-register.json``.
"""

from __future__ import annotations

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
